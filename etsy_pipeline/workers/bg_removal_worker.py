"""Background Removal Worker — AI background removal using rembg (isnet-general-use).

Processes raw generated images from the `image_generation` stage:
- Images in `misc_category` (characters, props, combos) are processed with rembg to produce transparent PNGs.
- Images in `pattern_scene_bonus_category` (patterns, scenes) skip AI removal and are directly copied.
- Performs post-stage GCS storage cleanup: deletes raw_images/ from GCS after background removal completes.

Responsibility: AI background removal for clipart images and GCS storage cleanup.
"""

from __future__ import annotations

import gc
import shutil
from datetime import datetime

try:
    from datetime import UTC
except ImportError:
    import datetime as dt

    UTC = dt.UTC
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from etsy_pipeline.utils.exceptions import BackgroundRemovalError
from etsy_pipeline.utils.logging import get_logger
from etsy_pipeline.workers.bg_removal_worker_config import (
    _PROGRESS_FLUSH_EVERY,
    CLEAR_GPU_EVERY_N_IMAGES,
    GPU_VM_HOURLY_RATE_USD,
    MISC_CATEGORY_SUBFOLDER,
    PATTERN_SCENE_BONUS_SUBFOLDER,
    REMBG_MODEL_NAME,
)

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.gcs_store import GCSStore
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


class BackgroundRemovalWorker:
    """Worker module for the background removal pipeline stage.

    Usage::

        worker = BackgroundRemovalWorker(settings=get_settings())
        job = worker.run(job)
    """

    STAGE_NAME: str = "bg_removal"

    def __init__(
        self,
        settings: Settings,
        mongo_store: MongoJobStore | None = None,
        gcs_store: GCSStore | None = None,
    ) -> None:
        """Initialise the BackgroundRemovalWorker.

        Args:
            settings: Loaded pipeline settings.
            mongo_store: Optional pre-built MongoJobStore.
            gcs_store: Optional pre-built GCSStore.
        """
        self._settings = settings
        self._mongo = mongo_store
        self._gcs = gcs_store

    def run(self, job: Job) -> Job:
        """Execute background removal for all raw clipart images of a Job.

        Args:
            job: The Job instance to process.

        Returns:
            The updated Job instance with stage status COMPLETED or FAILED.

        Raises:
            BackgroundRemovalError: If background removal fails catastrophically.
        """
        logger.info(
            f"[bg_removal] Starting stage for theme '{job.theme}' ({job.theme_slug})",
            extra={"job_id": job.job_id},
        )
        job.stages[self.STAGE_NAME].mark_running()

        raw_base_dir = (
            Path(self._settings.output_root)
            / job.date_folder
            / job.theme_slug
            / "raw_images"
        )
        no_bg_base_dir = (
            Path(self._settings.output_root)
            / job.date_folder
            / job.theme_slug
            / "no_bg"
        )
        no_bg_base_dir.mkdir(parents=True, exist_ok=True)

        # 1. Download raw images from GCS if not present locally
        self._ensure_raw_images_local(job, raw_base_dir)

        # 2. Gather raw images recursively across all subfolders under raw_images
        all_raw_files = sorted(list(raw_base_dir.rglob("*.png")))

        misc_raw_files = [
            f for f in all_raw_files if PATTERN_SCENE_BONUS_SUBFOLDER not in str(f)
        ]
        pattern_raw_files = [
            f for f in all_raw_files if PATTERN_SCENE_BONUS_SUBFOLDER in str(f)
        ]

        if not all_raw_files:
            error_msg = f"No raw images found to process in {raw_base_dir}"
            logger.error(f"[bg_removal] {error_msg}")
            job.stages[self.STAGE_NAME].mark_failed(error_msg)
            job.add_error(error_msg)
            raise BackgroundRemovalError(error_msg, job_id=job.job_id)

        total = len(all_raw_files)
        logger.info(
            f"[bg_removal] Total images to process: {total} "
            f"({len(misc_raw_files)} misc, {len(pattern_raw_files)} pattern/scene/bonus)"
        )

        start_time = datetime.now(UTC)
        processed_files: list[str] = []
        failed_count: int = 0

        # Lazy load rembg session
        try:
            from rembg import new_session, remove  # type: ignore[import-untyped]
        except ImportError as exc:
            raise BackgroundRemovalError(
                "rembg is not installed. Run: pip install 'rembg[gpu]'",
                job_id=job.job_id,
            ) from exc

        logger.info(f"[bg_removal] Initialising rembg model ({REMBG_MODEL_NAME})...")
        session = new_session(REMBG_MODEL_NAME)

        from tqdm import tqdm

        with tqdm(
            total=total,
            desc=f"✨ Removing Backgrounds '{job.theme}'",
            unit="img",
            dynamic_ncols=True,
        ) as pbar:
            for idx, img_path in enumerate(all_raw_files, start=1):
                fname = img_path.name
                is_pattern_or_scene = (
                    img_path.parent.name == PATTERN_SCENE_BONUS_SUBFOLDER
                    or any(k in fname.lower() for k in ["pattern", "scene", "bonus"])
                )

                subfolder = (
                    PATTERN_SCENE_BONUS_SUBFOLDER
                    if is_pattern_or_scene
                    else MISC_CATEGORY_SUBFOLDER
                )
                dest_dir = no_bg_base_dir / subfolder
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / fname

                # Skip if destination already exists
                if dest_path.exists():
                    processed_files.append(str(dest_path))
                    pbar.update(1)
                    continue

                if is_pattern_or_scene:
                    # Direct copy for pattern/scene/bonus (no AI background removal)
                    try:
                        shutil.copy(img_path, dest_path)
                        processed_files.append(str(dest_path))
                        logger.debug(
                            f"[bg_removal] Direct copy: {fname} → {subfolder}/"
                        )
                    except Exception as exc:
                        logger.error(f"[bg_removal] Copy failed for {fname}: {exc}")
                        failed_count += 1
                else:
                    # Run rembg AI background removal
                    input_img: Image.Image | None = None
                    output_img: Image.Image | None = None
                    try:
                        input_img = Image.open(img_path)
                        input_img.load()
                        output_img = remove(input_img, session=session)
                        output_img.save(dest_path)
                        processed_files.append(str(dest_path))
                    except Exception as exc:
                        logger.error(f"[bg_removal] rembg failed for {fname}: {exc}")
                        failed_count += 1
                    finally:
                        if input_img is not None:
                            input_img.close()
                        del input_img, output_img

                # Upload to GCS
                if dest_path.exists():
                    self._upload_no_bg_to_gcs(job, dest_path, subfolder)

                # Periodic GPU memory cleanup
                if idx % CLEAR_GPU_EVERY_N_IMAGES == 0:
                    clear_gpu()

                # Update progress
                elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
                cost = round(elapsed_hours * GPU_VM_HOURLY_RATE_USD, 4)
                pbar.update(1)
                pbar.set_postfix({"done": f"{idx}/{total}", "cost": f"${cost:.4f}"})

                if idx % _PROGRESS_FLUSH_EVERY == 0 or idx == total:
                    self._push_progress(job, idx, total, cost, gpu_hours=elapsed_hours)

        del session
        clear_gpu()

        elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
        final_cost = round(elapsed_hours * GPU_VM_HOURLY_RATE_USD, 4)

        if failed_count == total:
            error_msg = f"Background removal failed for all {total} images"
            job.stages[self.STAGE_NAME].mark_failed(error_msg)
            job.add_error(error_msg)
            raise BackgroundRemovalError(error_msg, job_id=job.job_id)

        # 3. Post-stage GCS storage cleanup: Purge raw_images from GCS to save storage
        self._purge_raw_images_from_gcs(job)

        job.stages[self.STAGE_NAME].mark_completed(
            cost_usd=final_cost,
            images_done=len(processed_files),
            images_total=total,
            gpu_hours=round(elapsed_hours, 4),
        )
        logger.info(
            f"[bg_removal] Stage complete for '{job.theme}': "
            f"{len(processed_files)}/{total} images processed | ${final_cost:.4f}"
        )
        return job

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_raw_images_local(self, job: Job, raw_base_dir: Path) -> None:
        """Ensure raw images exist locally, downloading from GCS if necessary."""
        raw_base_dir.mkdir(parents=True, exist_ok=True)

        gcs = self._get_gcs()
        if not gcs:
            return

        gcs_raw_prefix = f"Clipart/{job.date_folder}/{job.theme_slug}/raw_images/"
        gcs_objects = gcs.list_objects(gcs_raw_prefix)
        if not gcs_objects:
            logger.warning(
                f"[bg_removal] No GCS objects found under prefix {gcs_raw_prefix}"
            )
            return

        logger.info(f"[bg_removal] Syncing {len(gcs_objects)} raw images from GCS...")
        for obj_path in gcs_objects:
            # e.g. Clipart/<date>/<theme>/raw_images/misc_category/0001.png
            relative = obj_path[len(gcs_raw_prefix) :]
            local_target = raw_base_dir / relative
            if not local_target.exists():
                gcs.download_file(obj_path, local_target)

    def _upload_no_bg_to_gcs(self, job: Job, dest_path: Path, subfolder: str) -> None:
        """Upload transparent PNG to GCS under no_bg/<subfolder>/."""
        try:
            gcs = self._get_gcs()
            if gcs:
                gcs_path = gcs.make_image_path(
                    "no_bg",
                    job.date_folder,
                    job.theme_slug,
                    dest_path.name,
                    subfolder=subfolder,
                )
                gcs.upload_file(dest_path, gcs_path)
        except Exception as exc:
            logger.warning(
                f"[bg_removal] GCS upload failed for {dest_path.name}: {exc}"
            )

    def _purge_raw_images_from_gcs(self, job: Job) -> None:
        """Delete raw_images/ prefix from GCS post-stage to save storage."""
        try:
            gcs = self._get_gcs()
            if gcs:
                gcs_raw_prefix = (
                    f"Clipart/{job.date_folder}/{job.theme_slug}/raw_images/"
                )
                logger.info(
                    f"[bg_removal] Post-stage storage cleanup: deleting GCS prefix {gcs_raw_prefix}"
                )
                deleted_count = gcs.delete_prefix(gcs_raw_prefix)
                logger.info(
                    f"[bg_removal] Deleted {deleted_count} raw images from GCS to free storage."
                )
        except Exception as exc:
            logger.warning(f"[bg_removal] Failed to purge raw_images from GCS: {exc}")

    def _get_gcs(self) -> GCSStore | None:
        """Lazy load GCSStore."""
        if self._gcs is None and self._settings.gcs_bucket:
            from etsy_pipeline.services.gcs_store import GCSStore

            try:
                self._gcs = GCSStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[bg_removal] GCSStore init failed: {exc}")
        return self._gcs

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
                logger.warning(f"[bg_removal] MongoJobStore init failed: {exc}")
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
                logger.warning(f"[bg_removal] MongoDB progress push failed: {exc}")
