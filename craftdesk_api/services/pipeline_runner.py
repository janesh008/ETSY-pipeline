"""CraftDesk API — 6-Stage Pipeline execution runner and stage retry orchestrator."""

from __future__ import annotations

import asyncio
import json
import re
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from etsy_pipeline.config.settings import get_settings
from etsy_pipeline.models.job import Job
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

STAGE_DEFINITIONS = [
    {"stage_name": "image_gen", "label": "🎨 Stage 1: Image Generation (ComfyUI)"},
    {"stage_name": "bg_removal", "label": "✂️ Stage 2: Background Removal (rembg)"},
    {"stage_name": "upscaling", "label": "🔍 Stage 3: AI Upscaling (Real-ESRGAN / 4x)"},
    {"stage_name": "mockup_creation", "label": "🖼️ Stage 4: Mockup Creation"},
    {
        "stage_name": "pdf_generation",
        "label": "📄 Stage 5: Clickable PDF Wrap Generation",
    },
    {
        "stage_name": "metadata_generation",
        "label": "📝 Stage 6: Etsy Metadata (300 DPI Description & 13 Tags)",
    },
]

# In-memory store for pipeline jobs with disk persistence
_PIPELINE_JOBS_STORE: dict[str, dict[str, Any]] = {}
_ACTIVE_JOB_OBJECTS: dict[str, Job] = {}
_STOP_REQUESTS: set[str] = set()


def _get_cache_file() -> Path:
    return Path(get_settings().output_root) / ".jobs_cache.json"


def _save_jobs_cache() -> None:
    try:
        cache_file = _get_cache_file()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        serializable_jobs = {}
        for jid, data in _PIPELINE_JOBS_STORE.items():
            s_data = dict(data)
            if isinstance(s_data.get("created_at"), datetime):
                s_data["created_at"] = s_data["created_at"].isoformat()
            if isinstance(s_data.get("completed_at"), datetime):
                s_data["completed_at"] = s_data["completed_at"].isoformat()
            serializable_jobs[jid] = s_data
        cache_file.write_text(json.dumps(serializable_jobs, indent=2))
    except Exception as exc:
        logger.warning(f"[pipeline_runner] Failed to save jobs cache: {exc}")


def _load_jobs_cache() -> None:
    cache_file = _get_cache_file()
    if cache_file.exists():
        try:
            cached_jobs = json.loads(cache_file.read_text())
            _PIPELINE_JOBS_STORE.update(cached_jobs)
            logger.info(
                f"[pipeline_runner] Restored {len(cached_jobs)} jobs from disk cache."
            )
        except Exception as exc:
            logger.warning(f"[pipeline_runner] Failed to load jobs cache: {exc}")


_load_jobs_cache()


def _reconstruct_job_object(job_data: dict[str, Any]) -> Job:
    """Reconstruct a Job dataclass object from a job_data dict if memory was cleared."""
    settings = get_settings()
    theme_name = job_data.get("theme_name", "Clipart")
    date_folder = job_data.get("date_folder") or datetime.now(UTC).strftime("%Y-%m-%d")
    job = Job(
        job_id=job_data["job_id"],
        theme=theme_name,
        date_folder=date_folder,
        prompts=job_data.get(
            "prompts",
            {"MAIN_CHARACTER": [f"Digital watercolor clipart of {theme_name}"]},
        ),
        output_dir=str(
            Path(settings.output_root) / date_folder / theme_name.replace(" ", "_")
        ),
        metadata=job_data.get("metadata", {}),
    )
    if job_data.get("pdf_drive_link"):
        job.pdf_drive_link = job_data["pdf_drive_link"]
    if job_data.get("pdf_local_path"):
        job.pdf_path = job_data["pdf_local_path"]
    if job_data.get("mockups"):
        job.mockups = job_data["mockups"]
    if job_data.get("hero_image_url"):
        job.hero_image_url = job_data["hero_image_url"]
    return job


class PipelineRunnerService:
    """Orchestrates 6 pipeline stage execution using real etsy_pipeline worker modules."""

    @classmethod
    def stop_job(cls, job_id: str) -> dict[str, Any] | None:
        """Stop/cancel a running pipeline execution job."""
        _STOP_REQUESTS.add(job_id)
        job_data = _PIPELINE_JOBS_STORE.get(job_id)
        if job_data:
            job_data["status"] = "failed"
            curr_stage = job_data.get("current_stage")
            if curr_stage:
                stage_dict = next(
                    (s for s in job_data["stages"] if s["stage_name"] == curr_stage),
                    None,
                )
                if stage_dict and stage_dict["status"] == "running":
                    stage_dict["status"] = "failed"
                    stage_dict["error_message"] = "Pipeline execution stopped by user."
                    stage_dict["completed_at"] = datetime.now(UTC).isoformat()
        return job_data

    @classmethod
    def create_job(
        cls,
        user_id: str,
        theme_name: str,
        prompts: list[str] | None = None,
        prompt_file_path: str | None = None,
    ) -> dict[str, Any]:
        """Initialize a new 6-stage pipeline job and load prompts from GCS or local file.

        Preserves past date_folder if specified in prompt_file_path.
        """
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        _STOP_REQUESTS.discard(job_id)
        now = datetime.now(UTC)
        settings = get_settings()

        # Extract date_folder from prompt_file_path if present (e.g. Clipart/2026-07-22/...)
        extracted_date: str | None = None
        if prompt_file_path:
            m = re.search(r"Clipart/(\d{4}-\d{2}-\d{2})/", prompt_file_path)
            if m:
                extracted_date = m.group(1)

        job_kwargs: dict[str, Any] = {
            "job_id": job_id,
            "theme": theme_name,
            "prompt_file_path": prompt_file_path,
        }
        if extracted_date:
            job_kwargs["date_folder"] = extracted_date

        # Instantiate real etsy_pipeline Job model
        job = Job(**job_kwargs)

        # Inject prompts if prompt_file_path is provided
        if prompt_file_path:
            raw_text: str | None = None
            normalized_path = prompt_file_path.replace("\\", "/")

            # 1. Attempt downloading from GCS FIRST
            gcs_uri = normalized_path
            if not gcs_uri.startswith("gs://"):
                bucket_name = settings.gcs_bucket or "etsy-pixelbar-clipart"
                m_part = re.search(r"(Clipart/.*)", normalized_path, re.IGNORECASE)
                if m_part:
                    gcs_uri = f"gs://{bucket_name}/{m_part.group(1)}"
                else:
                    gcs_uri = f"gs://{bucket_name}/{normalized_path.lstrip('/')}"

            if gcs_uri.startswith("gs://"):
                try:
                    from google.cloud import storage

                    uri_parts = gcs_uri.replace("gs://", "").split("/", 1)
                    b_name = uri_parts[0]
                    blob_path = uri_parts[1]
                    client = storage.Client()
                    bucket = client.bucket(b_name)
                    blob = bucket.blob(blob_path)
                    if blob.exists():
                        raw_text = blob.download_as_text(encoding="utf-8")
                        logger.info(
                            f"[pipeline_runner] Downloaded prompt text from GCS: {gcs_uri}"
                        )
                except Exception as exc:
                    logger.warning(
                        f"[pipeline_runner] Could not download GCS prompt file '{gcs_uri}': {exc}"
                    )

            # 2. Fallback to local VM disk reading if GCS download did not return raw_text
            if not raw_text:
                p_file = Path(prompt_file_path)
                if not p_file.exists():
                    alt_path = Path(settings.output_root) / prompt_file_path
                    if alt_path.exists():
                        p_file = alt_path

                if p_file.exists() and p_file.is_file():
                    try:
                        raw_text = p_file.read_text(encoding="utf-8")
                        logger.info(
                            f"[pipeline_runner] Read prompt text from local disk: {p_file}"
                        )
                    except Exception as exc:
                        logger.warning(
                            f"[pipeline_runner] Could not read local prompt file '{prompt_file_path}': {exc}"
                        )

            if raw_text:
                try:
                    from etsy_pipeline.workers.prompt_worker import PromptWorker

                    pw = PromptWorker(settings=settings)
                    prompts_dict, roster = pw._parse_response(raw_text)
                    job.prompts = prompts_dict
                    job.character_roster = roster
                    job.raw_prompt_text = raw_text
                except Exception as exc:
                    logger.warning(
                        f"Could not parse prompt text using PromptWorker: {exc}"
                    )
                    lines = [
                        ln.strip()
                        for ln in raw_text.splitlines()
                        if ln.strip() and not ln.startswith("#")
                    ]
                    if lines:
                        job.prompts = {"main_category": lines}
            else:
                raise ValueError(
                    f"[pipeline_runner] Failed to locate/read prompt file from GCS or disk: {prompt_file_path}"
                )

        # Fallback if no prompts injected or prompt count is 0
        if job.total_prompt_count == 0 and prompts:
            job.prompts = {"MAIN_CHARACTER": prompts}

        if job.total_prompt_count == 0:
            job.prompts = {
                "MAIN_CHARACTER": [f"Digital watercolor clipart of {theme_name}"]
            }

        _ACTIVE_JOB_OBJECTS[job_id] = job

        stages = [
            {
                "stage_name": def_item["stage_name"],
                "label": def_item["label"],
                "status": "pending",
                "progress_percent": 0,
                "images_done": 0,
                "images_total": job.total_prompt_count,
                "elapsed_seconds": 0.0,
                "estimated_time_remaining_sec": None,
                "error_message": None,
                "stderr_log": None,
                "started_at": None,
                "completed_at": None,
            }
            for def_item in STAGE_DEFINITIONS
        ]

        job_data: dict[str, Any] = {
            "job_id": job_id,
            "user_id": user_id,
            "theme_name": theme_name,
            "prompt_file_path": prompt_file_path,
            "date_folder": job.date_folder,
            "prompts": job.prompts,
            "status": "running",
            "current_stage": "image_gen",
            "stages": stages,
            "hero_image_url": None,
            "mockups": [],
            "pdf_drive_link": None,
            "pdf_local_path": None,
            "metadata": job.metadata or {},
            "created_at": now,
            "completed_at": None,
        }

        _PIPELINE_JOBS_STORE[job_id] = job_data
        _save_jobs_cache()
        return job_data

    @classmethod
    def get_job(cls, job_id: str) -> dict[str, Any] | None:
        """Fetch job state by job_id."""
        return _PIPELINE_JOBS_STORE.get(job_id)

    @classmethod
    def list_jobs(cls, user_id: str) -> list[dict[str, Any]]:
        """Return list of all stored pipeline jobs for user_id sorted by created_at descending."""
        jobs = [j for j in _PIPELINE_JOBS_STORE.values() if j.get("user_id") == user_id]
        return sorted(jobs, key=lambda x: str(x.get("created_at", "")), reverse=True)


    @classmethod
    def _is_stage_100pct_complete(cls, job: Job, stage_name: str) -> bool:
        """Check if 100% of output files for a stage exist on local disk or GCS/Drive."""
        settings = get_settings()
        theme_slug = job.theme_slug
        date_folder = job.date_folder
        total_expected = job.total_prompt_count or 1

        if stage_name == "image_gen":
            dirs_to_check = [
                Path(settings.output_root)
                / "Clipart"
                / date_folder
                / theme_slug
                / "raw_images",
                Path(settings.output_root) / date_folder / theme_slug / "raw_images",
            ]
            for local_dir in dirs_to_check:
                if local_dir.exists():
                    pngs = [
                        f for f in local_dir.rglob("*.png") if f.stat().st_size > 10240
                    ]
                    if len(pngs) >= total_expected and total_expected > 0:
                        return True
            if settings.gcs_bucket:
                try:
                    from etsy_pipeline.services.gcs_store import GCSStore

                    gcs = GCSStore(settings=settings)
                    prefixes = [
                        f"Clipart/{date_folder}/{theme_slug}/raw_images/",
                        f"{date_folder}/{theme_slug}/raw_images/",
                    ]
                    for prefix in prefixes:
                        objs = gcs.list_objects(prefix)
                        png_objs = [o for o in objs if o.lower().endswith(".png")]
                        if len(png_objs) >= total_expected and total_expected > 0:
                            return True
                except Exception:
                    pass

            # Downstream completion fallback: raw_images is purged after bg_removal.
            # If bg_removal or upscaling outputs match total_expected, image_gen is 100% complete.
            if cls._is_stage_100pct_complete(
                job, "bg_removal"
            ) or cls._is_stage_100pct_complete(job, "upscaling"):
                return True

            return False

        elif stage_name == "bg_removal":
            dirs_to_check = [
                Path(settings.output_root)
                / "Clipart"
                / date_folder
                / theme_slug
                / "no_bg",
                Path(settings.output_root) / date_folder / theme_slug / "no_bg",
            ]
            for local_dir in dirs_to_check:
                if local_dir.exists():
                    pngs = [
                        f for f in local_dir.rglob("*.png") if f.stat().st_size > 10240
                    ]
                    if len(pngs) >= total_expected and total_expected > 0:
                        return True
            if settings.gcs_bucket:
                try:
                    from etsy_pipeline.services.gcs_store import GCSStore

                    gcs = GCSStore(settings=settings)
                    prefixes = [
                        f"Clipart/{date_folder}/{theme_slug}/no_bg/",
                        f"{date_folder}/{theme_slug}/no_bg/",
                    ]
                    for prefix in prefixes:
                        objs = gcs.list_objects(prefix)
                        png_objs = [o for o in objs if o.lower().endswith(".png")]
                        if len(png_objs) >= total_expected and total_expected > 0:
                            return True
                except Exception:
                    pass

            # Downstream completion fallback: if upscaling is 100% complete on Drive, bg_removal is complete.
            if cls._is_stage_100pct_complete(job, "upscaling"):
                return True

            return False

        elif stage_name == "upscaling":
            # Primary check: Google Drive folder Clipart/main_data/<date_folder>/<theme_slug>
            from etsy_pipeline.workers.upscale_worker_config import ETSY_DRIVE_FOLDER_ID

            parent_drive_id = settings.google_drive_folder_id or ETSY_DRIVE_FOLDER_ID
            if parent_drive_id:
                try:
                    from etsy_pipeline.services.google_drive import GoogleDriveService

                    drive = GoogleDriveService(settings=settings)
                    parts = ["Clipart", "main_data", date_folder, theme_slug]
                    folder_id = drive.find_folder_id_by_path(
                        parent_id=parent_drive_id, path_parts=parts
                    )
                    if folder_id:
                        files = drive.list_files_in_folder(folder_id)
                        png_files = [
                            f
                            for f in files
                            if f.get("name", "").lower().endswith(".png")
                        ]
                        if len(png_files) >= total_expected and total_expected > 0:
                            logger.info(
                                f"[pipeline_runner] Stage 'upscaling' is 100% complete — found {len(png_files)} PNGs in Google Drive folder '{'/'.join(parts)}'."
                            )
                            return True
                        else:
                            logger.info(
                                f"[pipeline_runner] Stage 'upscaling' in Google Drive contains {len(png_files)}/{total_expected} PNGs — stage will run."
                            )
                except Exception as exc:
                    logger.warning(
                        f"[pipeline_runner] Stage 'upscaling' Google Drive check failed: {exc}"
                    )

            # Local VM disk check removed for upscaling because upscaled files are delivered exclusively to Google Drive and purged locally.
            return False

        elif stage_name in ("mockup_creation", "pdf_generation"):
            local_base = Path(settings.output_root) / date_folder / theme_slug
            pdf_file = local_base / f"{theme_slug}.pdf"
            mockup_dir = local_base / "mockups"
            if pdf_file.exists() and mockup_dir.exists():
                mockup_pngs = sorted(
                    [
                        str(f)
                        for f in mockup_dir.glob("*.png")
                        if f.stat().st_size > 10240
                    ]
                )
                if len(mockup_pngs) >= 4 and pdf_file.stat().st_size > 10240:
                    job.pdf_path = str(pdf_file)
                    job.mockups = mockup_pngs
                    if mockup_pngs:
                        job.hero_image_url = mockup_pngs[0]
                    stored_job = _PIPELINE_JOBS_STORE.get(job.job_id)
                    if stored_job:
                        stored_job["pdf_local_path"] = str(pdf_file)
                        stored_job["mockups"] = mockup_pngs
                        if mockup_pngs:
                            stored_job["hero_image_url"] = mockup_pngs[0]
                    return True
            return False

        elif stage_name == "metadata_generation":
            if (
                job.metadata
                and job.metadata.get("title")
                and len(job.metadata.get("tags", [])) >= 5
            ):
                return True
            return False

        return False

    @classmethod
    def _execute_stage_worker_sync(cls, job: Job, stage_name: str) -> Job:
        """Synchronously execute the target etsy_pipeline worker for a stage."""
        settings = get_settings()

        if stage_name == "image_gen":
            from etsy_pipeline.workers.image_worker import ImageWorker

            worker = ImageWorker(settings=settings)
            return worker.run(job)

        elif stage_name == "bg_removal":
            from etsy_pipeline.workers.bg_removal_worker import BackgroundRemovalWorker

            worker = BackgroundRemovalWorker(settings=settings)
            return worker.run(job)

        elif stage_name == "upscaling":
            from etsy_pipeline.workers.upscale_worker import UpscaleWorker

            worker = UpscaleWorker(settings=settings)
            return worker.run(job)

        elif stage_name in ("mockup_creation", "pdf_generation"):
            from etsy_pipeline.workers.mockup_worker import MockupWorker

            worker = MockupWorker(settings=settings)
            return worker.run(job)

        elif stage_name == "metadata_generation":
            from etsy_pipeline.workers.listing_record_worker import ListingRecordWorker
            from etsy_pipeline.workers.metadata_worker import MetadataWorker

            worker = MetadataWorker(settings=settings)
            job = worker.run(job)
            record_worker = ListingRecordWorker(settings=settings)
            return record_worker.run(job)

        else:
            raise ValueError(f"Unknown stage name: {stage_name}")

    @classmethod
    async def run_stage_execution(
        cls, job_id: str, stage_name: str, force_fail: bool = False
    ) -> None:
        """Run execution of a single stage with real-time ETA and progress tracking."""
        job_data = _PIPELINE_JOBS_STORE.get(job_id)
        if not job_data:
            return

        settings = get_settings()

        job = _ACTIVE_JOB_OBJECTS.get(job_id)
        if not job:
            job = _reconstruct_job_object(job_data)
            _ACTIVE_JOB_OBJECTS[job_id] = job

        stage_dict = next(
            (s for s in job_data["stages"] if s["stage_name"] == stage_name), None
        )
        if not stage_dict:
            return

        start_dt = datetime.now(UTC)
        now_str = start_dt.isoformat()

        stage_dict["status"] = "running"
        stage_dict["started_at"] = now_str
        stage_dict["progress_percent"] = 5
        stage_dict["error_message"] = None
        stage_dict["stderr_log"] = None
        job_data["current_stage"] = stage_name

        if force_fail:
            await asyncio.sleep(0.3)
            stage_dict["status"] = "failed"
            stage_dict["progress_percent"] = 50
            stage_dict["error_message"] = (
                f"Simulated RuntimeError in stage [{stage_name}]"
            )
            stage_dict["stderr_log"] = (
                f"Traceback (most recent call last):\n"
                f'  File "etsy_pipeline/workers/{stage_name}_worker.py", line 42, in run\n'
                f"torch.cuda.OutOfMemoryError: Simulated failure requested."
            )
            job_data["status"] = "failed"
            return

        # Start real worker in a separate thread to keep uvicorn async loop non-blocking
        try:
            worker_task = asyncio.create_task(
                asyncio.to_thread(cls._execute_stage_worker_sync, job, stage_name)
            )

            # Map stage_name to internal stage key in Job
            internal_stage_key = {
                "image_gen": "image_generation",
                "bg_removal": "bg_removal",
                "upscaling": "upscaling",
                "mockup_creation": "mockups",
                "pdf_generation": "mockups",
                "metadata_generation": "metadata_generation",
            }.get(stage_name, stage_name)

            # Monitor progress while worker is running
            while not worker_task.done():
                await asyncio.sleep(0.5)

                if job_id in _STOP_REQUESTS:
                    worker_task.cancel()
                    stage_dict["status"] = "failed"
                    stage_dict["error_message"] = "Pipeline execution stopped by user."
                    job_data["status"] = "failed"
                    return

                elapsed_sec = round((datetime.now(UTC) - start_dt).total_seconds(), 1)
                stage_dict["elapsed_seconds"] = elapsed_sec

                st_res = job.stages.get(internal_stage_key)
                if st_res:
                    err_msg = getattr(st_res, "error_message", None)
                    log_msg = f"[{stage_name}] Status: {st_res.status}. Step {st_res.images_done}/{st_res.images_total or 1}. Elapsed: {elapsed_sec}s."
                    if err_msg:
                        log_msg += f"\nError: {err_msg}"
                    stage_dict["live_log"] = log_msg

                    if stage_name in ("mockup_creation", "pdf_generation"):
                        local_mockups_dir = (
                            Path(settings.output_root)
                            / job.date_folder
                            / job.theme_slug
                            / "mockups"
                        )
                        if local_mockups_dir.exists():
                            m_count = len(list(local_mockups_dir.glob("*.png")))
                            if m_count > 0:
                                stage_dict["images_done"] = m_count
                                stage_dict["images_total"] = max(4, m_count)
                                pct = int((m_count / 4) * 80) + 10
                                stage_dict["progress_percent"] = max(10, min(90, pct))
                            else:
                                stage_dict["progress_percent"] = min(
                                    90, max(10, int(elapsed_sec * 3))
                                )
                        else:
                            stage_dict["progress_percent"] = min(
                                90, max(10, int(elapsed_sec * 3))
                            )
                    elif st_res.images_total > 0:
                        stage_dict["images_done"] = st_res.images_done
                        stage_dict["images_total"] = st_res.images_total
                        pct = int((st_res.images_done / st_res.images_total) * 100)
                        stage_dict["progress_percent"] = max(5, min(99, pct))

                        # Calculate ETA
                        if st_res.images_done > 0:
                            avg_per_img = elapsed_sec / st_res.images_done
                            remaining_imgs = st_res.images_total - st_res.images_done
                            stage_dict["estimated_time_remaining_sec"] = round(
                                avg_per_img * remaining_imgs, 1
                            )
                    else:
                        stage_dict["progress_percent"] = min(
                            90, max(10, int(elapsed_sec * 5))
                        )

            # Await worker result
            job = await worker_task
            _ACTIVE_JOB_OBJECTS[job_id] = job

            # Mark completed
            completed_dt = datetime.now(UTC)
            stage_dict["status"] = "completed"
            stage_dict["progress_percent"] = 100
            stage_dict["completed_at"] = completed_dt.isoformat()
            stage_dict["elapsed_seconds"] = round(
                (completed_dt - start_dt).total_seconds(), 1
            )
            stage_dict["estimated_time_remaining_sec"] = 0.0

            # Update outputs in job_data
            if job.mockups:
                job_data["hero_image_url"] = job.mockups[0]
                job_data["mockups"] = job.mockups
            if job.pdf_drive_link:
                job_data["pdf_drive_link"] = job.pdf_drive_link
            if job.pdf_path:
                job_data["pdf_local_path"] = job.pdf_path
            if job.metadata:
                job_data["metadata"] = job.metadata

            # Check if all stages completed
            if all(s["status"] == "completed" for s in job_data["stages"]):
                job_data["status"] = "completed"
                job_data["completed_at"] = completed_dt
                job_data["current_stage"] = None

            _save_jobs_cache()

        except Exception as exc:
            error_str = str(exc)
            tb_str = traceback.format_exc()

            stage_dict["status"] = "failed"
            stage_dict["error_message"] = error_str
            stage_dict["stderr_log"] = tb_str
            job_data["status"] = "failed"
            _save_jobs_cache()
            logger.error(
                f"Pipeline stage '{stage_name}' failed: {error_str}", exc_info=True
            )

    @classmethod
    async def simulate_stage_execution(
        cls, job_id: str, stage_name: str, force_fail: bool = False
    ) -> None:
        """Bridge method for manual stage retries."""
        await cls.run_stage_execution(job_id, stage_name, force_fail=force_fail)

    @classmethod
    async def run_full_pipeline_async(
        cls, job_id: str, simulate_fail_stage: str | None = None
    ) -> None:
        """Run all 6 pipeline stages sequentially with 100% module checkpoint skipping."""
        job_data = _PIPELINE_JOBS_STORE.get(job_id)
        if not job_data:
            return

        job = _ACTIVE_JOB_OBJECTS.get(job_id)
        if not job:
            job = _reconstruct_job_object(job_data)
            _ACTIVE_JOB_OBJECTS[job_id] = job

        for stage in job_data["stages"]:
            s_name = stage["stage_name"]
            job_data["current_stage"] = s_name

            # Check if 100% of stage outputs exist in storage or stage is already marked completed
            if stage.get("status") == "completed" or cls._is_stage_100pct_complete(
                job, s_name
            ):
                logger.info(
                    f"[pipeline_runner] Stage '{s_name}' is 100% completed in storage — skipping worker execution."
                )
                stage["status"] = "completed"
                stage["progress_percent"] = 100
                stage["images_done"] = job.total_prompt_count
                stage["images_total"] = job.total_prompt_count
                stage["completed_at"] = (
                    stage.get("completed_at") or datetime.now(UTC).isoformat()
                )
                stage["error_message"] = None
                continue

            should_fail = s_name == simulate_fail_stage
            await cls.run_stage_execution(job_id, s_name, force_fail=should_fail)
            if job_data["status"] == "failed":
                break

        if all(s["status"] == "completed" for s in job_data["stages"]):
            job_data["status"] = "completed"
            job_data["completed_at"] = datetime.now(UTC)
            job_data["current_stage"] = None

        _save_jobs_cache()
