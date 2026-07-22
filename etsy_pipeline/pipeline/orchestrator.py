"""
Pipeline orchestrator — sequences pipeline stages with zero business logic.

The Pipeline class coordinates the execution of independent worker modules.
Each stage is called in order, receiving and returning a Job object.
The orchestrator handles only:
- Stage sequencing
- Error handling and status updates
- Logging

No business logic lives here. All implementation is in the workers.

Future agent compatibility:
    Each worker.run(job) call can be replaced with agent.execute(job)
    without changing the orchestrator.
"""

from __future__ import annotations

from typing import Protocol

from etsy_pipeline.config.settings import Settings, get_settings
from etsy_pipeline.models.job import Job, JobStatus
from etsy_pipeline.utils.exceptions import PipelineError
from etsy_pipeline.utils.logging import get_logger, setup_logging
from etsy_pipeline.workers.bg_removal_worker import BackgroundRemovalWorker
from etsy_pipeline.workers.csv_worker import CSVWorker
from etsy_pipeline.workers.etsy_worker import EtsyWorker
from etsy_pipeline.workers.image_worker import ImageWorker
from etsy_pipeline.workers.metadata_worker import MetadataWorker
from etsy_pipeline.workers.mockup_worker import MockupWorker
from etsy_pipeline.workers.prompt_worker import PromptWorker
from etsy_pipeline.workers.upscale_worker import UpscaleWorker

logger = get_logger(__name__)


class Worker(Protocol):
    """Protocol for pipeline stage workers."""

    def run(self, job: Job) -> Job:
        """Run the worker logic on a Job."""
        ...


class Pipeline:
    """
    Orchestrates the Etsy asset generation pipeline.

    Executes stages in sequence:
        Prompt Generation → Image Generation → Background Removal
        → Upscaling → Mockup → Metadata → CSV → Etsy Upload

    Currently only the Prompt Generation stage is implemented.
    Additional stages will be added one at a time as modules are built.

    Usage:
        pipeline = Pipeline()
        job = Job(theme="Lilo & Stitch", event_type="birthday")
        job = pipeline.run(job)

    Future FastAPI integration:
        @app.post("/generate")
        async def generate(request: GenerateRequest):
            job = Job(**request.dict())
            job = pipeline.run(job)
            return job
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the Pipeline with all worker instances.

        Args:
            settings: Optional Settings override. Uses global settings if not provided.
        """
        self._settings = settings or get_settings()

        # Initialize logging
        setup_logging(
            level=self._settings.log_level,
            log_format=self._settings.log_format,
        )

        # Initialize workers
        # Each worker is instantiated once and reused across jobs
        self._prompt_worker = PromptWorker(settings=self._settings)
        self._image_worker = ImageWorker(settings=self._settings)
        self._bg_removal_worker = BackgroundRemovalWorker(settings=self._settings)
        self._upscale_worker = UpscaleWorker(settings=self._settings)
        self._mockup_worker = MockupWorker(settings=self._settings)
        self._metadata_worker = MetadataWorker(settings=self._settings)
        self._csv_worker = CSVWorker(settings=self._settings)
        self._etsy_worker = EtsyWorker(settings=self._settings)

        logger.info("Pipeline initialized")

    def run(self, job: Job) -> Job:
        """
        Execute the full pipeline on a Job.

        Runs each stage sequentially. If a stage fails, the pipeline
        stops and the job is marked as FAILED with error details.

        Args:
            job: The Job to process.

        Returns:
            The updated Job after all stages complete (or after failure).
        """
        logger.info(
            f"Pipeline started for '{job.theme}' ({job.event_type})",
            extra={"job_id": job.job_id},
        )
        job.status = JobStatus.RUNNING
        job.add_log(f"Pipeline started for theme: {job.theme}")

        # Define the stage execution order
        # Each entry: (stage_name, worker)
        stages: list[tuple[str, Worker]] = [
            ("prompt_generation", self._prompt_worker),
            ("image_generation", self._image_worker),
            ("bg_removal", self._bg_removal_worker),
            ("upscaling", self._upscale_worker),
            ("mockups", self._mockup_worker),
            ("metadata_generation", self._metadata_worker),
            ("csv_generation", self._csv_worker),
            ("etsy_upload", self._etsy_worker),
        ]

        for stage_name, worker in stages:
            try:
                logger.info(
                    f"Running stage: {stage_name}",
                    extra={"job_id": job.job_id, "stage": stage_name},
                )
                job = worker.run(job)

            except PipelineError as e:
                error_msg = f"Stage '{stage_name}' failed: {e}"
                job.stages[stage_name].mark_failed(str(e))
                job.add_error(error_msg)
                job.status = JobStatus.FAILED
                logger.error(
                    error_msg,
                    extra={"job_id": job.job_id, "stage": stage_name},
                )
                break  # Stop pipeline on failure

            except Exception as e:
                error_msg = f"Unexpected error in stage '{stage_name}': {e}"
                job.stages[stage_name].mark_failed(str(e))
                job.add_error(error_msg)
                job.status = JobStatus.FAILED
                logger.error(
                    error_msg,
                    exc_info=True,
                    extra={"job_id": job.job_id, "stage": stage_name},
                )
                break

        else:
            # All stages completed successfully
            job.status = JobStatus.COMPLETED
            job.add_log("Pipeline completed successfully")

        logger.info(
            f"Pipeline finished with status: {job.status}",
            extra={"job_id": job.job_id},
        )
        return job

    def run_stage(self, job: Job, stage_name: str) -> Job:
        """
        Run a single stage by name.

        Useful for re-running a failed stage or testing individual stages.

        Args:
            job: The Job to process.
            stage_name: The stage to run (e.g., 'prompt_generation').

        Returns:
            The updated Job.
        """
        worker_map: dict[str, Worker] = {
            "prompt_generation": self._prompt_worker,
            "image_generation": self._image_worker,
            "bg_removal": self._bg_removal_worker,
            "upscaling": self._upscale_worker,
            "mockups": self._mockup_worker,
            "metadata_generation": self._metadata_worker,
            "csv_generation": self._csv_worker,
            "etsy_upload": self._etsy_worker,
        }

        worker = worker_map.get(stage_name)
        if not worker:
            raise ValueError(
                f"Unknown stage: '{stage_name}'. "
                f"Available stages: {list(worker_map.keys())}"
            )

        logger.info(
            f"Running single stage: {stage_name}",
            extra={"job_id": job.job_id, "stage": stage_name},
        )
        return worker.run(job)
