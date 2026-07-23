"""Storage Helper — unified 3-tier local VM verification and remote download fallback.

Checks for required pipeline files on the local VM disk first (fastest).
If missing, automatically attempts fallback download from GCS, and
secondarily from Google Drive.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

from etsy_pipeline.config.settings import Settings, get_settings
from etsy_pipeline.utils.logging import get_logger

if TYPE_CHECKING:
    from etsy_pipeline.services.gcs_store import GCSStore
    from etsy_pipeline.services.google_drive import GoogleDriveService

logger = get_logger(__name__)

DEFAULT_FILE_PATTERNS = ["*.png", "*.jpg", "*.jpeg", "*.pdf", "*.csv", "*.txt"]


def _get_local_matching_files(
    local_dir: Path, file_patterns: list[str]
) -> list[Path]:
    """Find all files in local_dir matching any pattern."""
    if not local_dir.exists():
        return []
    found: set[Path] = set()
    for pattern in file_patterns:
        found.update(local_dir.glob(pattern))
        found.update(local_dir.glob(pattern.upper()))
    return sorted(list(found))


def ensure_local_assets(
    local_dir: Path | str,
    gcs_prefix: str | None = None,
    drive_path_parts: list[str] | None = None,
    settings: Settings | None = None,
    file_patterns: list[str] | None = None,
    gcs_store: GCSStore | None = None,
    drive_service: GoogleDriveService | None = None,
) -> list[Path]:
    """Ensure required pipeline assets exist locally on the VM.

    1. Check local VM directory (`local_dir`). If matching files exist, return them immediately.
    2. If missing, attempt download from GCS using `gcs_prefix`.
    3. If still missing, attempt download from Google Drive using `drive_path_parts`.

    Args:
        local_dir: Local VM target directory.
        gcs_prefix: Optional GCS object prefix to download from.
        drive_path_parts: Optional path parts to resolve on Google Drive.
        settings: Pipeline settings.
        file_patterns: File extension globs to match (default: PNG, JPG, PDF, CSV, TXT).
        gcs_store: Pre-instantiated GCSStore (optional).
        drive_service: Pre-instantiated GoogleDriveService (optional).

    Returns:
        List of resolved local file Paths.
    """
    target_dir = Path(local_dir)
    patterns = file_patterns or DEFAULT_FILE_PATTERNS
    app_settings = settings or get_settings()

    # Step 1: Check Local VM Disk
    local_files = _get_local_matching_files(target_dir, patterns)
    if local_files:
        logger.debug(f"[storage_helper] Local VM hit: {len(local_files)} files in {target_dir}")
        return local_files

    # Step 2: GCS Fallback
    if gcs_prefix and app_settings.gcs_bucket:
        try:
            gcs = gcs_store
            if gcs is None:
                from etsy_pipeline.services.gcs_store import GCSStore

                gcs = GCSStore(settings=app_settings)

            objects = gcs.list_objects(gcs_prefix)
            if objects:
                logger.info(f"[storage_helper] Local VM miss. Downloading {len(objects)} objects from GCS ({gcs_prefix})...")
                target_dir.mkdir(parents=True, exist_ok=True)
                clean_prefix = gcs_prefix.rstrip("/") + "/"
                for obj_path in objects:
                    if obj_path.endswith("/"):
                        continue
                    filename = obj_path[len(clean_prefix):] if obj_path.startswith(clean_prefix) else Path(obj_path).name
                    dest_file = target_dir / filename
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if not dest_file.exists():
                        gcs.download_file(obj_path, dest_file)

                local_files = _get_local_matching_files(target_dir, patterns)
                if local_files:
                    return local_files
        except Exception as exc:
            logger.warning(f"[storage_helper] GCS fallback failed for prefix {gcs_prefix}: {exc}")

    # Step 3: Google Drive Fallback
    if drive_path_parts and app_settings.google_drive_folder_id:
        try:
            drive = drive_service
            if drive is None:
                from etsy_pipeline.services.google_drive import GoogleDriveService

                drive = GoogleDriveService(settings=app_settings)

            folder_id = drive.get_folder_id_by_path(
                parent_id=app_settings.google_drive_folder_id,
                path_parts=drive_path_parts,
            )

            service = drive._get_service()
            query = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get("files", [])

            if files:
                logger.info(f"[storage_helper] GCS miss. Downloading {len(files)} files from Google Drive ({'/'.join(drive_path_parts)})...")
                target_dir.mkdir(parents=True, exist_ok=True)

                from googleapiclient.http import (
                    MediaIoBaseDownload,  # type: ignore[import-untyped]
                )

                for f_info in files:
                    file_id = f_info["id"]
                    file_name = f_info["name"]
                    dest_file = target_dir / file_name

                    if not dest_file.exists():
                        request = service.files().get_media(fileId=file_id)
                        fh = io.FileIO(str(dest_file), "wb")
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            _, done = downloader.next_chunk()
                        fh.close()

                local_files = _get_local_matching_files(target_dir, patterns)
                if local_files:
                    return local_files
        except Exception as exc:
            logger.warning(f"[storage_helper] Google Drive fallback failed for path {drive_path_parts}: {exc}")

    return _get_local_matching_files(target_dir, patterns)
