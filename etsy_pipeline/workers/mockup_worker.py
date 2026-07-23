"""Mockup & PDF Generation Worker — phase 7 of the Etsy pipeline.

Generates mockup images by running the 'etsy mockup creator' subprocess,
shares the upscaled clipart folder publicly on Google Drive, creates a
clickable A4 PDF wrapper, and uploads all artifacts to GDrive and GCS.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from etsy_pipeline.utils.exceptions import PipelineError
from etsy_pipeline.utils.logging import get_logger
from etsy_pipeline.workers.mockup_worker_config import (
    DEJAVU_FONT_PATH,
    ETSY_DRIVE_FOLDER_ID,
    PDF_AUTHOR,
    PDF_CTA_TEXT,
    PDF_TITLE,
)

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.gcs_store import GCSStore
    from etsy_pipeline.services.google_drive import GoogleDriveService
    from etsy_pipeline.services.mongo_store import MongoJobStore

logger = get_logger(__name__)


class MockupError(PipelineError):
    """Exception raised during Mockup & PDF generation stage."""


class MockupWorker:
    """Worker module for running mockup and PDF download wrap generation."""

    STAGE_NAME: str = "mockups"

    def __init__(
        self,
        settings: Settings,
        mongo_store: MongoJobStore | None = None,
        gcs_store: GCSStore | None = None,
        drive_service: GoogleDriveService | None = None,
    ) -> None:
        """Initialise MockupWorker."""
        self._settings = settings
        self._mongo = mongo_store
        self._gcs = gcs_store
        self._drive = drive_service

    def run(self, job: Job) -> Job:
        """Run mockup generation and PDF wrapping for a Job.

        Args:
            job: State context object for the active job.

        Returns:
            The updated Job object.
        """
        logger.info(f"[mockups] Starting mockup stage for theme '{job.theme}'")
        job.stages[self.STAGE_NAME].mark_running()
        start_time = datetime.now(UTC)

        theme_slug = job.theme_slug

        # 1. Local workspace directory setup
        local_base_dir = Path(self._settings.output_root) / job.date_folder / theme_slug
        no_bg_dir = local_base_dir / "no_bg"
        mockups_local_dir = local_base_dir / "mockups"
        mockups_local_dir.mkdir(parents=True, exist_ok=True)

        # Download/ensure no_bg transparent images locally if missing (VM -> GCS -> Drive fallback)
        gcs_no_bg_prefix = f"Clipart/{job.date_folder}/{theme_slug}/no_bg/"
        drive_no_bg_parts = ["Clipart", "raw_data", job.date_folder, theme_slug, "no_bg"]
        from etsy_pipeline.services.storage_helper import ensure_local_assets

        ensure_local_assets(
            local_dir=no_bg_dir,
            gcs_prefix=gcs_no_bg_prefix,
            drive_path_parts=drive_no_bg_parts,
            settings=self._settings,
            gcs_store=self._gcs,
            drive_service=self._drive,
        )

        # Find first image for PDF preview before processing
        preview_image = self._find_first_image(no_bg_dir)

        # 2. Run Mockup Subprocess
        theme_display_name = job.theme or theme_slug.replace("_", " ")
        self._run_mockup_creator(no_bg_dir, mockups_local_dir, theme_name=theme_display_name)

        # 3. Share Upscaled GDrive Folder & Retrieve Link
        drive = self._get_drive()
        if not drive:
            raise MockupError("Google Drive Service is required.", job_id=job.job_id)

        # Walk to upscale path: Clipart/main_data/<date>/<theme_slug>
        upscale_parts = ["Clipart", "main_data", job.date_folder, theme_slug]
        try:
            upscale_folder_id = drive.get_folder_id_by_path(
                parent_id=ETSY_DRIVE_FOLDER_ID, path_parts=upscale_parts
            )
            public_folder_link = drive.share_folder_publicly(upscale_folder_id)
        except Exception as exc:
            error_msg = f"Failed to get/share upscale folder in Google Drive: {exc}"
            logger.error(f"[mockups] {error_msg}")
            job.stages[self.STAGE_NAME].mark_failed(error_msg)
            job.add_error(error_msg)
            raise MockupError(error_msg, job_id=job.job_id) from exc

        # 4. Generate Clickable A4 PDF wrapping
        pdf_local_path = local_base_dir / f"{theme_slug}.pdf"
        try:
            self._create_clickable_folder_pdf(
                preview_image, public_folder_link, pdf_local_path
            )
            logger.info(f"[mockups] Clickable PDF generated at: {pdf_local_path}")
        except Exception as exc:
            error_msg = f"ReportLab PDF generation failed: {exc}"
            logger.error(f"[mockups] {error_msg}")
            job.stages[self.STAGE_NAME].mark_failed(error_msg)
            job.add_error(error_msg)
            raise MockupError(error_msg, job_id=job.job_id) from exc

        # Update job fields
        job.pdf_path = str(pdf_local_path)
        job.pdf_drive_link = public_folder_link

        # 5. Delivery: Upload Mockups + PDF to GCS & Google Drive
        # Google Drive Raw Data path: Clipart/raw_data/<date>/<theme_slug>/
        raw_data_parts = ["Clipart", "raw_data", job.date_folder, theme_slug]
        try:
            # Upload local mockups folder to GDrive raw_data path
            drive.upload_folder_to_path(
                local_dir=mockups_local_dir,
                parent_id=ETSY_DRIVE_FOLDER_ID,
                path_parts=raw_data_parts + ["mockups"],
            )

            # Upload the PDF directly to GDrive raw_data path
            raw_data_folder_id = drive.get_folder_id_by_path(
                parent_id=ETSY_DRIVE_FOLDER_ID, path_parts=raw_data_parts
            )
            drive._upload_file_direct(pdf_local_path, raw_data_folder_id)
            logger.info("[mockups] Google Drive upload delivery complete.")
        except Exception as exc:
            error_msg = f"Google Drive raw_data upload failed: {exc}"
            logger.error(f"[mockups] {error_msg}")
            job.stages[self.STAGE_NAME].mark_failed(error_msg)
            job.add_error(error_msg)
            raise MockupError(error_msg, job_id=job.job_id) from exc

        # GCS upload
        gcs = self._get_gcs()
        if gcs:
            try:
                # Upload PDF
                gcs_pdf_key = (
                    f"Clipart/{job.date_folder}/{theme_slug}/pdf/{theme_slug}.pdf"
                )
                gcs.upload_file(pdf_local_path, gcs_pdf_key)

                # Upload Mockups
                mockup_files = list(mockups_local_dir.rglob("*.png"))
                for file_path in mockup_files:
                    relative_path = file_path.relative_to(mockups_local_dir)
                    gcs_key = f"Clipart/{job.date_folder}/{theme_slug}/mockups/{relative_path}"
                    gcs.upload_file(file_path, gcs_key)

                logger.info("[mockups] GCS backup delivery complete.")
            except Exception as exc:
                logger.warning(f"[mockups] GCS upload failed: {exc}")

        # Finalize job status
        elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
        cost = round(elapsed_hours * 0.5, 4)  # Simple compute estimation

        job.stages[self.STAGE_NAME].mark_completed(
            cost_usd=cost,
            images_done=len(list(mockups_local_dir.glob("*.png"))),
            images_total=len(list(mockups_local_dir.glob("*.png"))),
            gpu_hours=0.0,
        )

        return job

    def _run_mockup_creator(
        self, input_dir: Path, output_dir: Path, theme_name: str | None = None
    ) -> None:
        """Run the 'etsy mockup creator' subprocess."""
        mockup_creator_dir = Path(self._settings.project_root) / "etsy mockup creator"
        if not mockup_creator_dir.exists():
            raise MockupError(
                f"Mockup creator directory not found at: {mockup_creator_dir}"
            )

        logger.info(
            f"[mockups] Running mockup generator subprocess. Input: {input_dir}"
        )
        try:
            cmd = [
                sys.executable,
                "-m",
                "src.main",
                "--theme",
                str(input_dir.resolve()),
                "--output",
                str(output_dir.resolve()),
                "--templates",
                str((mockup_creator_dir / "templates").resolve()),
            ]
            if theme_name and theme_name.strip():
                cmd.extend(["--theme-name", theme_name.strip()])

            result = subprocess.run(
                cmd,
                cwd=str(mockup_creator_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("[mockups] Mockup creator subprocess completed successfully.")
            logger.debug(result.stdout)
        except subprocess.CalledProcessError as exc:
            error_msg = f"Mockup creator subprocess failed: {exc.stderr or exc.stdout}"
            logger.error(f"[mockups] {error_msg}")
            raise MockupError(error_msg) from exc

    def _create_clickable_folder_pdf(
        self, image_path: Path, folder_link: str, output_pdf: Path
    ) -> None:
        """Render beautiful A4 single-page download wrapping catalog PDF."""
        page_width, page_height = A4
        pdf = canvas.Canvas(str(output_pdf), pagesize=(page_width, page_height))
        pdf.setTitle(PDF_TITLE)
        pdf.setAuthor(PDF_AUTHOR)

        # Background Fill (Warm Beige)
        pdf.setFillColorRGB(0.98, 0.96, 0.92)
        pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # White inner card container
        margin = 36
        card_w = page_width - (margin * 2)
        card_h = page_height - (margin * 2)
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.roundRect(margin, margin, card_w, card_h, 12, fill=1, stroke=0)

        # Header Text
        pdf.setFillColorRGB(0.25, 0.15, 0.05)
        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawCentredString(
            page_width / 2, page_height - 90, "Your Clipart Collection Is Ready!"
        )

        # Font fallback setup
        font_name = "Helvetica"
        if Path(DEJAVU_FONT_PATH).exists():
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", DEJAVU_FONT_PATH))
                font_name = "DejaVuSans"
            except Exception:
                pass

        pdf.setFont(font_name, 13)
        pdf.setFillColorRGB(0.4, 0.4, 0.4)
        message = (
            "Tap anywhere on the image or use the button below to access your files."
        )
        pdf.drawCentredString(page_width / 2, page_height - 120, message)

        # Image calculations
        from PIL import Image

        with Image.open(image_path) as preview:
            image_width, image_height = preview.size

        max_width = card_w - 60
        max_height = page_height - 340
        scale = min(max_width / image_width, max_height / image_height)
        draw_width = image_width * scale
        draw_height = image_height * scale
        image_x = (page_width - draw_width) / 2
        image_y = (page_height - draw_height) / 2 + 20

        # Draw visual preview image
        pdf.drawImage(
            ImageReader(str(image_path)),
            image_x,
            image_y,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )

        # Link image area
        pdf.linkURL(
            folder_link,
            (image_x, image_y, image_x + draw_width, image_y + draw_height),
            relative=0,
            thickness=0,
        )

        # Button Layout
        btn_w, btn_h = 240, 48
        btn_x = (page_width - btn_w) / 2
        btn_y = margin + 40

        pdf.setFillColorRGB(0.15, 0.45, 0.85)
        pdf.roundRect(btn_x, btn_y, btn_w, btn_h, 8, fill=1, stroke=0)

        pdf.setFont("Helvetica-Bold", 14)
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.drawCentredString(page_width / 2, btn_y + 17, PDF_CTA_TEXT)

        # Button link mapping
        pdf.linkURL(
            folder_link,
            (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h),
            relative=0,
            thickness=0,
        )

        pdf.save()

    def _ensure_no_bg_images_local(self, job: Job, no_bg_dir: Path) -> None:
        """Download no_bg images from GCS if not present locally."""
        gcs = self._get_gcs()
        if not gcs:
            return

        gcs_no_bg_prefix = (
            f"Clipart/{job.date_folder}/{job.theme_slug}/no_bg/"
        )
        gcs_objects = gcs.list_objects(gcs_no_bg_prefix)
        if not gcs_objects:
            logger.warning(
                f"[mockups] No GCS objects found under prefix {gcs_no_bg_prefix}"
            )
            return

        no_bg_dir.mkdir(parents=True, exist_ok=True)
        for obj_path in gcs_objects:
            relative = obj_path[len(gcs_no_bg_prefix) :]
            local_target = no_bg_dir / relative
            local_target.parent.mkdir(parents=True, exist_ok=True)
            if not local_target.exists():
                gcs.download_file(obj_path, local_target)

    def _find_first_image(self, folder_path: Path) -> Path:
        """Find the first supported image in a folder."""
        supported_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        image_paths = sorted(
            p
            for p in folder_path.rglob("*")
            if p.is_file() and p.suffix.lower() in supported_extensions
        )
        if not image_paths:
            raise MockupError(f"No image found in: {folder_path}")
        return image_paths[0]

    def _get_gcs(self) -> GCSStore | None:
        """Lazy load GCSStore."""
        if self._gcs is None and self._settings.gcs_bucket:
            from etsy_pipeline.services.gcs_store import GCSStore

            try:
                self._gcs = GCSStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[mockups] GCSStore init failed: {exc}")
        return self._gcs

    def _get_drive(self) -> GoogleDriveService | None:
        """Lazy load GoogleDriveService."""
        if self._drive is None:
            from etsy_pipeline.services.google_drive import GoogleDriveService

            try:
                self._drive = GoogleDriveService(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[mockups] GoogleDriveService init failed: {exc}")
        return self._drive
