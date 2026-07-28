"""CraftDesk API — 6-Stage Pipeline execution runner and stage retry orchestrator."""

from __future__ import annotations

import asyncio
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

# In-memory store for pipeline jobs
_PIPELINE_JOBS_STORE: dict[str, dict[str, Any]] = {}
_ACTIVE_JOB_OBJECTS: dict[str, Job] = {}
_STOP_REQUESTS: set[str] = set()


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
        """Initialize a new 6-stage pipeline job and load prompts from GCS or local file."""
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        _STOP_REQUESTS.discard(job_id)
        now = datetime.now(UTC)
        settings = get_settings()

        # Instantiate real etsy_pipeline Job model
        job = Job(
            job_id=job_id,
            theme=theme_name,
            prompt_file_path=prompt_file_path,
        )

        # Inject prompts if prompt_file_path is provided
        if prompt_file_path:
            raw_text: str | None = None
            if prompt_file_path.startswith("gs://"):
                try:
                    from google.cloud import storage

                    uri_parts = prompt_file_path.replace("gs://", "").split("/", 1)
                    bucket_name = uri_parts[0]
                    blob_path = uri_parts[1]
                    client = storage.Client()
                    bucket = client.bucket(bucket_name)
                    blob = bucket.blob(blob_path)
                    raw_text = blob.download_as_text(encoding="utf-8")
                except Exception as exc:
                    logger.warning(
                        f"Could not download GCS prompt file '{prompt_file_path}': {exc}"
                    )
            else:
                p_file = Path(prompt_file_path)
                if not p_file.exists():
                    # Check under output_root / Clipart / ...
                    alt_path = Path(settings.output_root) / prompt_file_path
                    if alt_path.exists():
                        p_file = alt_path

                if p_file.exists():
                    try:
                        raw_text = p_file.read_text(encoding="utf-8")
                    except Exception as exc:
                        logger.warning(
                            f"Could not read local prompt file '{prompt_file_path}': {exc}"
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
                    job.prompts = {"MAIN_CHARACTER": lines}
                    job.raw_prompt_text = raw_text

        # Fallback if no prompts injected
        if not job.prompts and prompts:
            job.prompts = {"MAIN_CHARACTER": prompts}

        if not job.prompts:
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
            "prompts": job.prompts,
            "status": "running",
            "current_stage": "image_gen",
            "stages": stages,
            "hero_image_url": None,
            "mockups": [],
            "metadata": job.metadata or {},
            "created_at": now,
            "completed_at": None,
        }

        _PIPELINE_JOBS_STORE[job_id] = job_data
        return job_data

    @classmethod
    def get_job(cls, job_id: str) -> dict[str, Any] | None:
        """Fetch job state by job_id."""
        return _PIPELINE_JOBS_STORE.get(job_id)

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
            from etsy_pipeline.workers.metadata_worker import MetadataWorker

            worker = MetadataWorker(settings=settings)
            return worker.run(job)

        else:
            raise ValueError(f"Unknown stage name: {stage_name}")

    @classmethod
    async def run_stage_execution(
        cls, job_id: str, stage_name: str, force_fail: bool = False
    ) -> None:
        """Run execution of a single stage with real-time ETA and progress tracking."""
        job_data = _PIPELINE_JOBS_STORE.get(job_id)
        job = _ACTIVE_JOB_OBJECTS.get(job_id)
        if not job_data or not job:
            return

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
                    if st_res.images_total > 0:
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
                        # Fallback heuristic progress percent
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
            if job.metadata:
                job_data["metadata"] = job.metadata

            # Check if all stages completed
            if all(s["status"] == "completed" for s in job_data["stages"]):
                job_data["status"] = "completed"
                job_data["completed_at"] = completed_dt
                job_data["current_stage"] = None

        except Exception as exc:
            error_str = str(exc)
            tb_str = traceback.format_exc()

            stage_dict["status"] = "failed"
            stage_dict["error_message"] = error_str
            stage_dict["stderr_log"] = tb_str
            job_data["status"] = "failed"
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
        """Run all 6 pipeline stages sequentially."""
        job_data = _PIPELINE_JOBS_STORE.get(job_id)
        if not job_data:
            return

        for stage in job_data["stages"]:
            s_name = stage["stage_name"]
            should_fail = s_name == simulate_fail_stage
            await cls.run_stage_execution(job_id, s_name, force_fail=should_fail)
            if job_data["status"] == "failed":
                break
