"""CSV Worker — phase 8b of the Etsy pipeline.

Generates and maintains the consolidated per-date Etsy listings CSV file.
Row schema aligns with Etsy bulk upload specifications and internal upload tools.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from etsy_pipeline.utils.exceptions import PipelineError
from etsy_pipeline.utils.logging import get_logger

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.gcs_store import GCSStore
    from etsy_pipeline.services.google_drive import GoogleDriveService

logger = get_logger(__name__)

CSV_HEADERS: list[str] = [
    "JOB_ID",
    "THEME",
    "TITLE",
    "DESCRIPTION",
    "TAGS",
    "PRICE",
    "QUANTITY",
    "WHO_MADE",
    "WHEN_MADE",
    "TAXONOMY_ID",
    "TYPE",
    "IS_DIGITAL",
    "MATERIALS",
    "SECTION_ID",
    "MOCKUP_GCS_PREFIX",
    "PDF_DRIVE_LINK",
    "LISTING_ID",
    "LISTING_URL",
]


class CSVGenerationError(PipelineError):
    """Exception raised during CSV generation stage."""


class CSVWorker:
    """Worker for appending/updating job listing rows in consolidated CSV files."""

    STAGE_NAME: str = "csv_generation"

    def __init__(
        self,
        settings: Settings,
        gcs_store: GCSStore | None = None,
        drive_service: GoogleDriveService | None = None,
    ) -> None:
        """Initialise CSVWorker."""
        self._settings = settings
        self._gcs = gcs_store
        self._drive = drive_service

    def run(self, job: Job) -> Job:
        """Append or update the Job's Etsy listing data in the date's CSV file.

        Args:
            job: The Job context containing metadata.

        Returns:
            Updated Job object with csv_path set.

        Raises:
            CSVGenerationError: If CSV writing or storage sync fails.
        """
        logger.info(f"[csv] Consolidating CSV row for job {job.job_id} ({job.theme})")
        stage = job.stages[self.STAGE_NAME]
        stage.mark_running()

        date_dir = Path(self._settings.output_root) / job.date_folder
        date_dir.mkdir(parents=True, exist_ok=True)
        csv_file_path = date_dir / "all_listings.csv"

        gcs_key = f"csv/{job.date_folder}/all_listings.csv"

        # 1. Download/ensure existing CSV locally if missing (VM -> GCS -> Drive fallback)
        from etsy_pipeline.services.storage_helper import ensure_local_assets

        ensure_local_assets(
            local_dir=date_dir,
            gcs_prefix=gcs_key,
            drive_path_parts=["Clipart", "csv", job.date_folder],
            settings=self._settings,
            file_patterns=["all_listings.csv"],
            gcs_store=self._gcs,
            drive_service=self._drive,
        )

        # 2. Read existing rows
        existing_rows: list[dict[str, str]] = []
        if csv_file_path.exists():
            try:
                with open(csv_file_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)
            except Exception as exc:
                logger.warning(f"[csv] Failed to read existing CSV {csv_file_path}: {exc}")

        # 3. Construct job row dictionary
        row_dict = self._build_row_dict(job)

        # 4. Upsert row based on JOB_ID
        updated = False
        for idx, row in enumerate(existing_rows):
            if row.get("JOB_ID") == job.job_id:
                existing_rows[idx] = row_dict
                updated = True
                break

        if not updated:
            existing_rows.append(row_dict)

        # 5. Write back to local CSV file
        try:
            with open(csv_file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                writer.writeheader()
                writer.writerows(existing_rows)
            logger.info(f"[csv] Saved consolidated CSV to: {csv_file_path}")
        except Exception as exc:
            error_msg = f"Failed to write CSV file {csv_file_path}: {exc}"
            logger.error(f"[csv] {error_msg}")
            stage.mark_failed(error_msg)
            job.add_error(error_msg)
            raise CSVGenerationError(error_msg, job_id=job.job_id) from exc

        # 6. Dual Storage Sync: Upload updated CSV to both GCS and Google Drive
        if gcs:
            try:
                gcs.upload_file(csv_file_path, gcs_key)
                logger.info(f"[csv] Uploaded consolidated CSV to GCS: gs://{gcs_key}")
            except Exception as exc:
                logger.warning(f"[csv] Failed to upload CSV to GCS: {exc}")

        drive = self._get_drive()
        if drive and self._settings.google_drive_folder_id:
            try:
                drive_path_parts = ["Clipart", "csv", job.date_folder]
                target_folder_id = drive._get_or_create_folder_by_path(
                    parent_id=self._settings.google_drive_folder_id,
                    path_parts=drive_path_parts,
                )
                drive._upload_file_direct(csv_file_path, target_folder_id)
                logger.info(
                    f"[csv] Uploaded consolidated CSV to Google Drive path: {'/'.join(drive_path_parts)}"
                )
            except Exception as exc:
                logger.warning(f"[csv] Failed to upload CSV to Google Drive: {exc}")

        job.csv_path = str(csv_file_path)
        stage.mark_completed()
        return job

    def _build_row_dict(self, job: Job) -> dict[str, str]:
        """Convert Job state into Etsy listing CSV row mapping."""
        tags_str = "|".join(job.etsy_tags) if job.etsy_tags else ""
        escaped_desc = (job.etsy_description or "").replace("\r\n", "\n").replace("\n", "\\n")
        mockup_gcs_prefix = f"Clipart/{job.date_folder}/{job.theme_slug}/mockups/"

        return {
            "JOB_ID": job.job_id,
            "THEME": job.theme,
            "TITLE": job.etsy_title or "",
            "DESCRIPTION": escaped_desc,
            "TAGS": tags_str,
            "PRICE": f"{job.listing_price_usd:.2f}",
            "QUANTITY": str(job.listing_quantity),
            "WHO_MADE": "i_did",
            "WHEN_MADE": "made_to_order",
            "TAXONOMY_ID": "110",  # Standard Etsy taxonomy node ID for Clip Art
            "TYPE": "download",
            "IS_DIGITAL": "true",
            "MATERIALS": "PNG,Digital Download,Transparent Background",
            "SECTION_ID": "",
            "MOCKUP_GCS_PREFIX": mockup_gcs_prefix,
            "PDF_DRIVE_LINK": job.pdf_drive_link or "",
            "LISTING_ID": job.etsy_listing_id or "",
            "LISTING_URL": job.etsy_listing_url or "",
        }

    def _get_gcs(self) -> GCSStore | None:
        """Lazy load GCSStore."""
        if self._gcs is None and self._settings.gcs_bucket:
            from etsy_pipeline.services.gcs_store import GCSStore

            try:
                self._gcs = GCSStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[csv] GCSStore init failed: {exc}")
        return self._gcs

    def _get_drive(self) -> GoogleDriveService | None:
        """Lazy load GoogleDriveService."""
        if self._drive is None:
            from etsy_pipeline.services.google_drive import GoogleDriveService

            try:
                self._drive = GoogleDriveService(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[csv] GoogleDriveService init failed: {exc}")
        return self._drive
