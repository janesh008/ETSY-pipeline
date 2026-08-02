"""Listing Record Worker — phase 8b of the Etsy pipeline.

Generates and stores a per-theme ``listing.json`` file containing all Etsy
listing fields in native JSON types. Replaces the shared per-date CSV approach.

Responsibility: Write per-theme listing.json to local disk, GCS, and Google Drive
after metadata generation completes.

Storage paths:
    Local VM:     output/<date>/<theme_slug>/metadata/listing.json
    GCS:          Clipart/<date>/<theme_slug>/metadata/listing.json
    Google Drive: Clipart/raw_data/<date>/<theme_slug>/metadata/listing.json
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from etsy_pipeline.utils.exceptions import ListingRecordError
from etsy_pipeline.utils.logging import get_logger

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.gcs_store import GCSStore
    from etsy_pipeline.services.google_drive import GoogleDriveService

logger = get_logger(__name__)


class ListingRecordWorker:
    """Worker for writing per-theme listing.json records after metadata generation."""

    STAGE_NAME: str = "listing_record"

    def __init__(
        self,
        settings: Settings,
        gcs_store: GCSStore | None = None,
        drive_service: GoogleDriveService | None = None,
    ) -> None:
        """Initialise ListingRecordWorker."""
        self._settings = settings
        self._gcs = gcs_store
        self._drive = drive_service

    def run(self, job: Job) -> Job:
        """Write per-theme listing.json for the completed job.

        Args:
            job: The Job context with etsy_title, etsy_description, etsy_tags populated.

        Returns:
            Updated Job object with listing_record_path set.

        Raises:
            ListingRecordError: If writing or storage sync fails.
        """
        logger.info(
            f"[listing_record] Writing listing.json for job {job.job_id} ({job.theme})"
        )
        stage = job.stages[self.STAGE_NAME]
        stage.mark_running()

        # Local path: output/<date>/<theme_slug>/metadata/listing.json
        local_dir = (
            Path(self._settings.output_root)
            / job.date_folder
            / job.theme_slug
            / "metadata"
        )
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / "listing.json"

        # 1. Build record dict
        record = self._build_record(job)

        # 2. Write to local disk
        try:
            local_path.write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info(f"[listing_record] Saved listing.json to: {local_path}")
        except Exception as exc:
            error_msg = f"Failed to write listing.json to {local_path}: {exc}"
            logger.error(f"[listing_record] {error_msg}")
            stage.mark_failed(error_msg)
            job.add_error(error_msg)
            raise ListingRecordError(error_msg, job_id=job.job_id) from exc

        # 3. Upload to GCS: Clipart/<date>/<theme_slug>/metadata/listing.json
        gcs_key = f"Clipart/{job.date_folder}/{job.theme_slug}/metadata/listing.json"
        gcs = self._get_gcs()
        if gcs:
            try:
                gcs.upload_file(local_path, gcs_key)
                logger.info(
                    f"[listing_record] Uploaded listing.json to GCS: gs://{self._settings.gcs_bucket}/{gcs_key}"
                )
            except Exception as exc:
                logger.warning(
                    f"[listing_record] Failed to upload listing.json to GCS: {exc}"
                )

        # 4. Upload to Google Drive: Clipart/raw_data/<date>/<theme_slug>/metadata/
        drive = self._get_drive()
        if drive and self._settings.google_drive_folder_id:
            try:
                drive_path_parts = [
                    "Clipart",
                    "raw_data",
                    job.date_folder,
                    job.theme_slug,
                    "metadata",
                ]
                target_folder_id = drive._get_or_create_folder_by_path(
                    parent_id=self._settings.google_drive_folder_id,
                    path_parts=drive_path_parts,
                )
                drive._upload_file_direct(local_path, target_folder_id)
                logger.info(
                    f"[listing_record] Uploaded listing.json to Google Drive path: {'/'.join(drive_path_parts)}"
                )
            except Exception as exc:
                logger.warning(
                    f"[listing_record] Failed to upload listing.json to Google Drive: {exc}"
                )

        job.listing_record_path = str(local_path)
        stage.mark_completed()
        logger.info(f"[listing_record] listing.json complete for '{job.theme}'")
        return job

    def _build_record(self, job: Job) -> dict[str, Any]:
        """Convert Job state into a per-theme listing record dict.

        Args:
            job: The pipeline Job object.

        Returns:
            Dict with all Etsy listing fields in native Python types.
        """
        return {
            "job_id": job.job_id,
            "theme": job.theme,
            "theme_slug": job.theme_slug,
            "date_folder": job.date_folder,
            "generated_at": datetime.now(UTC).isoformat(),
            "etsy_title": job.etsy_title or "",
            "etsy_description": job.etsy_description or "",
            "etsy_tags": list(job.etsy_tags),
            "listing_price_usd": float(job.listing_price_usd),
            "listing_quantity": int(job.listing_quantity),
            "who_made": "i_did",
            "when_made": "made_to_order",
            "taxonomy_id": 6844,  # Craft Supplies & Tools > Clip Art & Image Files
            "type": "download",
            "is_digital": True,
            "is_ai_created": True,
            "renewal_option": "automatic",
            "craft_type": [
                "Card making & stationery",
                "Collage",
                "Kids' crafts"
            ],
            "materials": ["PNG", "Digital Download", "Transparent Background"],

            "mockup_gcs_prefix": (
                f"Clipart/{job.date_folder}/{job.theme_slug}/mockups/"
            ),
            "pdf_drive_link": job.pdf_drive_link or "",
            "etsy_listing_id": job.etsy_listing_id or "",
            "etsy_listing_url": job.etsy_listing_url or "",
        }


    def _get_gcs(self) -> GCSStore | None:
        """Lazy load GCSStore."""
        if self._gcs is None and self._settings.gcs_bucket:
            from etsy_pipeline.services.gcs_store import GCSStore

            try:
                self._gcs = GCSStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[listing_record] GCSStore init failed: {exc}")
        return self._gcs

    def _get_drive(self) -> GoogleDriveService | None:
        """Lazy load GoogleDriveService."""
        if self._drive is None:
            from etsy_pipeline.services.google_drive import GoogleDriveService

            try:
                self._drive = GoogleDriveService(settings=self._settings)
            except Exception as exc:
                logger.warning(
                    f"[listing_record] GoogleDriveService init failed: {exc}"
                )
        return self._drive
