"""GCS Store — upload, download, and delete files in Google Cloud Storage.

Provides a clean wrapper around the ``google-cloud-storage`` client for all
pipeline artifact I/O: prompt text files, raw images, bg-removed images,
upscaled images, and mockups.

Responsibility: All GCS read/write/delete operations for pipeline artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from etsy_pipeline.utils.logging import get_logger

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings

logger = get_logger(__name__)


class GCSStore:
    """Google Cloud Storage wrapper for pipeline artifact management.

    All uploads/downloads are intra-region (VM ↔ GCS bucket in the same
    GCP region), which means transfer is free of charge.

    Path convention::

        gs://{bucket}/prompts/{date}/{theme_slug}.txt
        gs://{bucket}/raw_images/{date}/{theme_slug}/{filename}
        gs://{bucket}/no_bg/{date}/{theme_slug}/{filename}
        gs://{bucket}/upscaled/{date}/{theme_slug}/{filename}
        gs://{bucket}/mockups/{date}/{theme_slug}/{filename}

    Usage::

        store = GCSStore(settings=get_settings())
        gcs_path = store.upload_file(local_path, \"prompts/2026-07-20/Lilo_and_Stitch.txt\")
        store.download_file(\"prompts/2026-07-20/Lilo_and_Stitch.txt\", local_path)
        store.delete_prefix(\"raw_images/2026-07-20/Lilo_and_Stitch/\")
    """

    def __init__(self, settings: Settings) -> None:
        """Initialise the GCS client.

        Uses Application Default Credentials (ADC) — the attached GCP Service
        Account on the VM, or ``GOOGLE_APPLICATION_CREDENTIALS`` locally.

        Args:
            settings: Loaded pipeline settings (used for ``gcs_bucket``).

        Raises:
            ImportError: If ``google-cloud-storage`` is not installed.
            ValueError: If ``GCS_BUCKET`` is not configured in settings.
        """
        try:
            from google.cloud import storage  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "google-cloud-storage is not installed. "
                "Run: pip install google-cloud-storage"
            ) from exc

        if not settings.gcs_bucket:
            raise ValueError(
                "[configuration] GCS_BUCKET is not configured in settings. "
                "Set GCS_BUCKET=<your-bucket-name> in your .env file."
            )

        self._bucket_name = settings.gcs_bucket
        self._client = storage.Client(project=settings.gcp_project_id or None)
        self._bucket = self._client.bucket(self._bucket_name)
        logger.info(f"[gcs] GCS client initialised (bucket={self._bucket_name})")

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_file(self, local_path: str | Path, gcs_object_path: str) -> str:
        """Upload a single local file to GCS.

        Args:
            local_path: Absolute or relative path to the local file.
            gcs_object_path: Destination object path inside the bucket
                (e.g. ``"prompts/2026-07-20/Lilo_and_Stitch.txt"``).

        Returns:
            The full GCS URI of the uploaded object (``gs://bucket/path``).

        Raises:
            FileNotFoundError: If ``local_path`` does not exist.
            RuntimeError: If the GCS upload fails.
        """
        local = Path(local_path)
        if not local.exists():
            raise FileNotFoundError(f"[gcs] Local file not found: {local}")

        blob = self._bucket.blob(gcs_object_path)
        try:
            blob.upload_from_filename(str(local))
        except Exception as exc:
            raise RuntimeError(
                f"[gcs] Upload failed for {local} → gs://{self._bucket_name}/{gcs_object_path}: {exc}"
            ) from exc

        gcs_uri = f"gs://{self._bucket_name}/{gcs_object_path}"
        logger.info(f"[gcs] Uploaded {local.name} → {gcs_uri}")
        return gcs_uri

    def upload_folder(self, local_dir: str | Path, gcs_prefix: str) -> list[str]:
        """Recursively upload all files in a local directory to a GCS prefix.

        Args:
            local_dir: Local directory to upload.
            gcs_prefix: GCS path prefix (e.g. ``"raw_images/2026-07-20/Lilo_and_Stitch/"``).

        Returns:
            List of GCS URIs for all uploaded files.
        """
        local_dir = Path(local_dir)
        if not local_dir.is_dir():
            raise NotADirectoryError(f"[gcs] Not a directory: {local_dir}")

        uris: list[str] = []
        for file_path in sorted(local_dir.rglob("*")):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(local_dir)
            gcs_path = f"{gcs_prefix.rstrip('/')}/{relative.as_posix()}"
            uri = self.upload_file(file_path, gcs_path)
            uris.append(uri)

        logger.info(
            f"[gcs] Uploaded {len(uris)} files from {local_dir} → gs://{self._bucket_name}/{gcs_prefix}"
        )
        return uris

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_file(self, gcs_object_path: str, local_path: str | Path) -> Path:
        """Download a single GCS object to a local path.

        Args:
            gcs_object_path: Object path inside the bucket.
            local_path: Destination local file path (parent dirs are created).

        Returns:
            Path to the downloaded local file.

        Raises:
            RuntimeError: If the GCS download fails.
        """
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        blob = self._bucket.blob(gcs_object_path)
        try:
            blob.download_to_filename(str(local))
        except Exception as exc:
            raise RuntimeError(
                f"[gcs] Download failed for gs://{self._bucket_name}/{gcs_object_path}: {exc}"
            ) from exc

        logger.info(
            f"[gcs] Downloaded gs://{self._bucket_name}/{gcs_object_path} → {local}"
        )
        return local

    def download_as_text(self, gcs_object_path: str, encoding: str = "utf-8") -> str:
        """Download a GCS object and return its contents as a string.

        Useful for reading prompt .txt files without saving to disk.

        Args:
            gcs_object_path: Object path inside the bucket.
            encoding: Text encoding (default: utf-8).

        Returns:
            File contents as a string.

        Raises:
            RuntimeError: If the GCS download fails.
        """
        blob = self._bucket.blob(gcs_object_path)
        try:
            return blob.download_as_text(encoding=encoding)
        except Exception as exc:
            raise RuntimeError(
                f"[gcs] Download-as-text failed for gs://{self._bucket_name}/{gcs_object_path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_prefix(self, gcs_prefix: str) -> int:
        """Delete all GCS objects under a given prefix (simulates folder delete).

        Used for post-stage cleanup: deletes raw_images/ after bg_removal
        completes, and upscaled/ after delivery to Google Drive.

        Args:
            gcs_prefix: GCS path prefix to delete (e.g. ``"raw_images/2026-07-20/Lilo_and_Stitch/"``).

        Returns:
            Number of objects deleted.
        """
        blobs = list(self._client.list_blobs(self._bucket_name, prefix=gcs_prefix))
        if not blobs:
            logger.warning(
                f"[gcs] delete_prefix: no objects found under gs://{self._bucket_name}/{gcs_prefix}"
            )
            return 0

        for blob in blobs:
            blob.delete()

        logger.info(
            f"[gcs] Deleted {len(blobs)} objects under gs://{self._bucket_name}/{gcs_prefix}"
        )
        return len(blobs)

    def delete_file(self, gcs_object_path: str) -> None:
        """Delete a single GCS object.

        Args:
            gcs_object_path: Object path inside the bucket to delete.
        """
        self._bucket.blob(gcs_object_path).delete()
        logger.info(f"[gcs] Deleted gs://{self._bucket_name}/{gcs_object_path}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def exists(self, gcs_object_path: str) -> bool:
        """Check whether a GCS object exists.

        Args:
            gcs_object_path: Object path inside the bucket.

        Returns:
            True if the object exists, False otherwise.
        """
        return self._bucket.blob(gcs_object_path).exists()

    def list_objects(self, gcs_prefix: str) -> list[str]:
        """List all object paths under a GCS prefix.

        Args:
            gcs_prefix: GCS path prefix to list.

        Returns:
            List of GCS object names (relative to bucket root).
        """
        return [
            blob.name
            for blob in self._client.list_blobs(self._bucket_name, prefix=gcs_prefix)
        ]

    @staticmethod
    def make_prompt_path(date_folder: str, theme_slug: str) -> str:
        """Build the canonical GCS path for a prompt text file.

        Args:
            date_folder: Date string (e.g. ``"2026-07-20"``).
            theme_slug: URL-safe theme identifier (e.g. ``"Lilo_and_Stitch"``).

        Returns:
            GCS object path string.
        """
        return f"Clipart/{date_folder}/{theme_slug}/{theme_slug}.txt"

    @staticmethod
    def make_image_path(
        prefix: str, date_folder: str, theme_slug: str, filename: str
    ) -> str:
        """Build a canonical GCS path for a pipeline image artifact.

        Args:
            prefix: Stage prefix — one of ``raw_images``, ``no_bg``, ``upscaled``, ``mockups``.
            date_folder: Date string (e.g. ``"2026-07-20"``).
            theme_slug: URL-safe theme identifier.
            filename: Image filename (e.g. ``"0001.png"``).

        Returns:
            GCS object path string.
        """
        return f"Clipart/{date_folder}/{theme_slug}/{prefix}/{filename}"
