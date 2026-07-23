"""Upscale Worker — AI upscaling using Real-ESRGAN.

Processes background-removed transparent images from the `bg_removal` stage:
- Reads all images from no_bg/ (both misc and pattern subfolders).
- Runs Real-ESRGAN with 4x-UltraSharp weights, using dynamic tile scaling on OOM.
- Standardizes output resolution to 4096px on the longest side at 300 DPI.
- Delivers files directly to Google Drive under Clipart/main_data/<date>/<theme_slug>/.
- Keeps no_bg/ images intact on GCS (does NOT delete them).

Responsibility: AI image upscaling and Google Drive file delivery.
"""

from __future__ import annotations

import gc
import urllib.request
from datetime import datetime

try:
    from datetime import UTC
except ImportError:
    import datetime as dt

    UTC = dt.UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from etsy_pipeline.utils.exceptions import UpscalingError
from etsy_pipeline.utils.logging import get_logger
from etsy_pipeline.workers.upscale_worker_config import (
    _PROGRESS_FLUSH_EVERY,
    CLEAR_GPU_EVERY_N_IMAGES,
    DRIVE_PATH_PARTS_PREFIX,
    ETSY_DRIVE_FOLDER_ID,
    GPU_VM_HOURLY_RATE_USD,
    PRE_PAD,
    START_TILE_SIZE,
    TARGET_DPI,
    TARGET_MAX_SIDE,
    TILE_PAD,
    UPSCALE_MODEL_URL,
)

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.gcs_store import GCSStore
    from etsy_pipeline.services.google_drive import GoogleDriveService
    from etsy_pipeline.services.mongo_store import MongoJobStore

logger = get_logger(__name__)


def clear_gpu() -> None:
    """Clear Python garbage collector and PyTorch CUDA cache if available."""
    gc.collect()
    try:
        import torch  # type: ignore[import-untyped]

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


class UpscaleWorker:
    """Worker module for the image upscaling pipeline stage.

    Usage::

        worker = UpscaleWorker(settings=get_settings())
        job = worker.run(job)
    """

    STAGE_NAME: str = "upscaling"

    def __init__(
        self,
        settings: Settings,
        mongo_store: MongoJobStore | None = None,
        gcs_store: GCSStore | None = None,
        drive_service: GoogleDriveService | None = None,
    ) -> None:
        """Initialise the UpscaleWorker.

        Args:
            settings: Loaded pipeline settings.
            mongo_store: Optional pre-built MongoJobStore.
            gcs_store: Optional pre-built GCSStore.
            drive_service: Optional pre-built GoogleDriveService.
        """
        self._settings = settings
        self._mongo = mongo_store
        self._gcs = gcs_store
        self._drive = drive_service

    def _ensure_model_downloaded(self) -> Path:
        """Ensure the upscaling model weights are downloaded to the models directory."""
        model_dir = Path(self._settings.output_root).parent / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "4x-UltraSharp.pth"

        if not model_path.exists():
            logger.info(
                f"[upscaling] Downloading 4x-UltraSharp model from {UPSCALE_MODEL_URL}..."
            )
            try:
                urllib.request.urlretrieve(UPSCALE_MODEL_URL, model_path)
                logger.info("[upscaling] Model download complete.")
            except Exception as exc:
                raise UpscalingError(
                    f"Failed to download upscaling model weights: {exc}"
                ) from exc
        return model_path

    def _build_upsampler(self, model_path: Path, tile: int) -> Any:
        """Build the RealESRGANer instance with specified tile size."""
        import sys

        import torchvision.transforms.functional as functional  # type: ignore[import-untyped]

        sys.modules["torchvision.transforms.functional_tensor"] = functional

        from basicsr.archs.rrdbnet_arch import RRDBNet  # type: ignore[import-untyped]
        from realesrgan import RealESRGANer  # type: ignore[import-untyped]

        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=4,
        )
        return RealESRGANer(
            scale=4,
            model_path=str(model_path),
            model=model,
            tile=tile,
            tile_pad=TILE_PAD,
            pre_pad=PRE_PAD,
            half=True,
            device="cuda",
        )

    def run(self, job: Job) -> Job:
        """Execute AI upscaling for all background-removed transparent images.

        Args:
            job: The Job instance to process.

        Returns:
            The updated Job instance.
        """
        logger.info(
            f"[upscaling] Starting upscaling stage for theme '{job.theme}' ({job.theme_slug})",
            extra={"job_id": job.job_id},
        )
        job.stages[self.STAGE_NAME].mark_running()

        no_bg_base_dir = (
            Path(self._settings.output_root)
            / job.date_folder
            / job.theme_slug
            / "no_bg"
        )
        upscaled_dir = (
            Path(self._settings.output_root)
            / job.date_folder
            / job.theme_slug
            / "upscaled"
        )
        upscaled_dir.mkdir(parents=True, exist_ok=True)

        # 1. Ensure no_bg images exist locally (VM -> GCS -> Drive fallback)
        gcs_no_bg_prefix = f"Clipart/{job.date_folder}/{job.theme_slug}/no_bg/"
        drive_no_bg_parts = ["Clipart", "raw_data", job.date_folder, job.theme_slug, "no_bg"]
        from etsy_pipeline.services.storage_helper import ensure_local_assets

        ensure_local_assets(
            local_dir=no_bg_base_dir,
            gcs_prefix=gcs_no_bg_prefix,
            drive_path_parts=drive_no_bg_parts,
            settings=self._settings,
            gcs_store=self._gcs,
            drive_service=self._drive,
        )

        # Gather all no_bg images recursively (misc_category and pattern_scene_bonus_category)
        no_bg_files = sorted(list(no_bg_base_dir.rglob("*.png")))

        if not no_bg_files:
            error_msg = (
                f"No background-removed images found to upscale in {no_bg_base_dir}"
            )
            logger.error(f"[upscaling] {error_msg}")
            job.stages[self.STAGE_NAME].mark_failed(error_msg)
            job.add_error(error_msg)
            raise UpscalingError(error_msg, job_id=job.job_id)

        total = len(no_bg_files)
        logger.info(f"[upscaling] Found {total} images to upscale")

        model_path = self._ensure_model_downloaded()

        # Import AI modules
        try:
            import cv2  # type: ignore[import-untyped]
            import torch  # type: ignore[import-untyped]
        except ImportError as exc:
            raise UpscalingError(
                "Upscaling dependencies (opencv-python, torch, realesrgan) are not installed.",
                job_id=job.job_id,
            ) from exc

        tile = START_TILE_SIZE
        logger.info(f"[upscaling] Building upsampler with tile size = {tile}")
        upsampler = self._build_upsampler(model_path, tile)

        start_time = datetime.now(UTC)
        processed_files: list[str] = []
        failed_count: int = 0

        from tqdm import tqdm

        with tqdm(
            total=total,
            desc=f"🚀 Upscaling '{job.theme}'",
            unit="img",
            dynamic_ncols=True,
        ) as pbar:
            for idx, img_path in enumerate(no_bg_files, start=1):
                fname = img_path.name
                dest_path = upscaled_dir / fname

                # Skip if already upscaled locally
                if dest_path.exists():
                    processed_files.append(str(dest_path))
                    pbar.update(1)
                    continue

                img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
                if img is None:
                    logger.error(f"[upscaling] Failed to read: {fname}")
                    failed_count += 1
                    pbar.update(1)
                    continue

                output = None
                # Dynamic tile-size fallback logic on CUDA OOM
                for attempt_tile in [tile, 256, 128]:
                    try:
                        if attempt_tile != tile:
                            logger.info(
                                f"[upscaling] Rebuilding upsampler with tile size = {attempt_tile}"
                            )
                            del upsampler
                            clear_gpu()
                            upsampler = self._build_upsampler(model_path, attempt_tile)
                            tile = attempt_tile

                        output, _ = upsampler.enhance(
                            img, outscale=4, alpha_upsampler="realesrgan"
                        )
                        break
                    except torch.cuda.OutOfMemoryError:
                        logger.warning(
                            f"[upscaling] VRAM OOM on {fname} with tile={attempt_tile}. Retrying with smaller tile..."
                        )
                        clear_gpu()
                        continue
                    except Exception as exc:
                        logger.error(
                            f"[upscaling] RealESRGAN exception on {fname}: {exc}"
                        )
                        break

                if output is None:
                    logger.error(
                        f"[upscaling] Failed to upscale {fname} (unrecoverable OOM/error)"
                    )
                    failed_count += 1
                    del img
                    pbar.update(1)
                    continue

                try:
                    # Save output
                    cv2.imwrite(str(dest_path), output)

                    # Standardize side length to 4096px at 300 DPI
                    with Image.open(dest_path) as pil_img:
                        max_side = max(pil_img.width, pil_img.height)
                        if max_side != TARGET_MAX_SIDE:
                            scale = TARGET_MAX_SIDE / max_side
                            resized = pil_img.resize(
                                (
                                    int(pil_img.width * scale),
                                    int(pil_img.height * scale),
                                ),
                                Image.Resampling.LANCZOS,
                            )
                            resized.save(dest_path, dpi=(TARGET_DPI, TARGET_DPI))
                        else:
                            pil_img.save(dest_path, dpi=(TARGET_DPI, TARGET_DPI))

                    processed_files.append(str(dest_path))
                    logger.debug(f"[upscaling] Standarised: {fname} (4096px @ 300 DPI)")
                except Exception as exc:
                    logger.error(
                        f"[upscaling] Saving/formatting failed for {fname}: {exc}"
                    )
                    failed_count += 1
                finally:
                    del img, output

                # Periodic GPU garbage collection
                if idx % CLEAR_GPU_EVERY_N_IMAGES == 0:
                    clear_gpu()

                # Update progress
                elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
                cost = round(elapsed_hours * GPU_VM_HOURLY_RATE_USD, 4)
                pbar.update(1)
                pbar.set_postfix({"done": f"{idx}/{total}", "cost": f"${cost:.4f}"})

                if idx % _PROGRESS_FLUSH_EVERY == 0 or idx == total:
                    self._push_progress(job, idx, total, cost, gpu_hours=elapsed_hours)

        del upsampler
        clear_gpu()

        elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
        final_cost = round(elapsed_hours * GPU_VM_HOURLY_RATE_USD, 4)

        if failed_count == total:
            error_msg = f"Upscaling failed for all {total} images"
            job.stages[self.STAGE_NAME].mark_failed(error_msg)
            job.add_error(error_msg)
            raise UpscalingError(error_msg, job_id=job.job_id)

        # 2. Upload all upscaled files directly to Google Drive path: Clipart/main_data/<date>/<theme_slug>
        self._upload_to_google_drive(job, upscaled_dir)

        # 3. Clean up local upscaled directory so upscaled images are not retained on local VM
        import shutil
        try:
            if upscaled_dir.exists():
                shutil.rmtree(upscaled_dir, ignore_errors=True)
                logger.info(f"[upscaling] Purged upscaled images from local VM disk: {upscaled_dir}")
        except Exception as exc:
            logger.warning(f"[upscaling] Failed to purge local upscaled directory: {exc}")

        job.stages[self.STAGE_NAME].mark_completed(
            cost_usd=final_cost,
            images_done=len(processed_files),
            images_total=total,
            gpu_hours=round(elapsed_hours, 4),
        )
        logger.info(
            f"[upscaling] Stage complete for '{job.theme}': "
            f"{len(processed_files)}/{total} images upscaled & uploaded to Google Drive | ${final_cost:.4f}"
        )
        return job

    # ── Internal Helpers ───────────────────────────────────────────────

    def _ensure_no_bg_images_local(self, job: Job, no_bg_base_dir: Path) -> None:
        """Download no_bg images from GCS if not present locally."""
        gcs = self._get_gcs()
        if not gcs:
            return

        gcs_no_bg_prefix = f"Clipart/{job.date_folder}/{job.theme_slug}/no_bg/"
        gcs_objects = gcs.list_objects(gcs_no_bg_prefix)
        if not gcs_objects:
            logger.warning(
                f"[upscaling] No GCS objects found under prefix {gcs_no_bg_prefix}"
            )
            return

        logger.info(
            f"[upscaling] Syncing {len(gcs_objects)} transparent images from GCS..."
        )
        for obj_path in gcs_objects:
            relative = obj_path[len(gcs_no_bg_prefix) :]
            local_target = no_bg_base_dir / relative
            if not local_target.exists():
                gcs.download_file(obj_path, local_target)

    def _upload_to_google_drive(self, job: Job, upscaled_dir: Path) -> None:
        """Upload all upscaled images directly to Google Drive under nested path."""
        drive = self._get_drive()
        if not drive:
            logger.warning(
                "[upscaling] Google Drive service not initialized. Skipping upload."
            )
            return

        # Folder structure: Clipart/main_data/<date>/<theme_slug>
        path_parts = DRIVE_PATH_PARTS_PREFIX + [job.date_folder, job.theme_slug]
        logger.info(
            f"[upscaling] Uploading upscaled files to Google Drive path: {'/'.join(path_parts)}"
        )

        try:
            drive.upload_folder_to_path(
                local_dir=upscaled_dir,
                parent_id=ETSY_DRIVE_FOLDER_ID,
                path_parts=path_parts,
            )
            logger.info("[upscaling] Google Drive delivery complete.")
        except Exception as exc:
            logger.error(f"[upscaling] Google Drive upload failed: {exc}")
            raise UpscalingError(
                f"Google Drive upload failed: {exc}", job_id=job.job_id
            ) from exc

    def _get_gcs(self) -> GCSStore | None:
        """Lazy load GCSStore."""
        if self._gcs is None and self._settings.gcs_bucket:
            from etsy_pipeline.services.gcs_store import GCSStore

            try:
                self._gcs = GCSStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[upscaling] GCSStore init failed: {exc}")
        return self._gcs

    def _get_drive(self) -> GoogleDriveService | None:
        """Lazy load GoogleDriveService."""
        if self._drive is None:
            from etsy_pipeline.services.google_drive import GoogleDriveService

            try:
                self._drive = GoogleDriveService(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[upscaling] GoogleDriveService init failed: {exc}")
        return self._drive

    def _push_progress(
        self,
        job: Job,
        images_done: int,
        images_total: int,
        cost_usd: float,
        gpu_hours: float = 0.0,
    ) -> None:
        """Push progress updates to MongoDB."""
        if self._mongo is None and self._settings.mongo_uri:
            from etsy_pipeline.services.mongo_store import MongoJobStore

            try:
                self._mongo = MongoJobStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[upscaling] MongoJobStore init failed: {exc}")
                return

        if self._mongo:
            try:
                self._mongo.update_stage_progress(
                    job.job_id,
                    self.STAGE_NAME,
                    images_done=images_done,
                    images_total=images_total,
                    cost_usd=cost_usd,
                    gpu_hours=gpu_hours,
                )
            except Exception as exc:
                logger.warning(f"[upscaling] MongoDB progress push failed: {exc}")
