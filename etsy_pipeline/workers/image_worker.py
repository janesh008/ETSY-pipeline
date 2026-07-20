"""Image Worker — generates images via ComfyUI for all prompts in a Job.

Polls Firestore for jobs where ``prompt_generation`` is COMPLETED and
``image_generation`` is PENDING, claims them atomically, submits each
prompt to ComfyUI's HTTP API, uploads output PNGs to GCS, and updates
Firestore with live progress and cost every N images.

Responsibility: ComfyUI-based image generation for all pipeline prompt sets.
"""

from __future__ import annotations

import json
import random
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from etsy_pipeline.utils.exceptions import ImageGenerationError
from etsy_pipeline.utils.logging import get_logger
from etsy_pipeline.workers.image_worker_config import (
    COMFYUI_HISTORY_ENDPOINT,
    COMFYUI_MAX_RETRIES,
    COMFYUI_POLL_INTERVAL_SECONDS,
    COMFYUI_PROMPT_ENDPOINT,
    COMFYUI_TIMEOUT_SECONDS,
    COMFYUI_VIEW_ENDPOINT,
    GCS_RAW_IMAGES_PREFIX,
    GPU_VM_HOURLY_RATE_USD,
    WORKFLOW_JSON_PATH,
    WORKFLOW_PROMPT_NODE_ID,
    WORKFLOW_SAVE_NODE_ID,
    WORKFLOW_SEED_NODE_ID,
)

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.firestore_store import FirestoreJobStore
    from etsy_pipeline.services.gcs_store import GCSStore

logger = get_logger(__name__)

# How many images to generate before flushing a Firestore progress update
_PROGRESS_FLUSH_EVERY: int = 5


class ImageWorker:
    """Generates images for all prompts in a Job using ComfyUI.

    Submits each prompt text to the local ComfyUI server, polls for
    completion, downloads the resulting PNG, saves it locally, and
    uploads it to GCS. Progress and cost are reported to Firestore
    after every ``_PROGRESS_FLUSH_EVERY`` images.

    Usage (from ``scripts/run_image_worker.py``)::

        worker = ImageWorker(settings=get_settings())
        job = worker.run(job)
    """

    STAGE_NAME: str = "image_generation"

    def __init__(
        self,
        settings: Settings,
        firestore_store: FirestoreJobStore | None = None,
        gcs_store: GCSStore | None = None,
    ) -> None:
        """Initialise the ImageWorker.

        Args:
            settings: Loaded pipeline settings.
            firestore_store: Optional pre-built FirestoreJobStore (injected for testing).
            gcs_store: Optional pre-built GCSStore (injected for testing).
        """
        self._settings = settings
        self._firestore = firestore_store
        self._gcs = gcs_store
        self._workflow_template: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, job: Job) -> Job:
        """Run image generation for all prompts in a Job.

        Generates one image per prompt across all sections, tracking progress
        and cost in Firestore. Saves images locally to the job output directory
        and uploads each PNG to GCS.

        Args:
            job: The Job object with ``prompts`` populated by PromptWorker.

        Returns:
            The updated Job with ``generated_images`` populated.

        Raises:
            ImageGenerationError: If ComfyUI is unreachable or generation fails for too many prompts.
        """
        stage = job.stages[self.STAGE_NAME]
        stage.mark_running()

        # Flatten prompts: [(section_name, prompt_text), ...]
        all_prompts: list[tuple[str, str]] = []
        for section, prompts in job.prompts.items():
            for p in prompts:
                all_prompts.append((section, p))

        if not all_prompts:
            raise ImageGenerationError(
                "No prompts found in job — cannot generate images.", job_id=job.job_id
            )

        total = len(all_prompts)
        stage.images_total = total
        stage.images_done = 0

        # Push initial state
        self._push_progress(job, 0, total, 0.0)

        # Output dir for this job
        output_dir = (
            Path(self._settings.output_root)
            / job.date_folder
            / job.theme_slug
            / "raw_images"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load ComfyUI workflow template once
        workflow = self._load_workflow()

        start_time = datetime.now(UTC)
        generated: list[str] = []
        failed_count: int = 0

        for idx, (section, prompt_text) in enumerate(all_prompts, start=1):
            logger.info(
                f"[image_worker] [{idx}/{total}] {section}: {prompt_text[:80]}..."
            )

            # Build workflow for this prompt
            prompt_workflow = self._inject_prompt(workflow, prompt_text)

            # Submit to ComfyUI with retries
            image_path: Path | None = None
            for attempt in range(1, COMFYUI_MAX_RETRIES + 1):
                try:
                    prompt_id = self._submit_prompt(prompt_workflow)
                    image_bytes, filename = self._wait_for_output(prompt_id)
                    image_path = output_dir / f"{idx:04d}_{filename}"
                    image_path.write_bytes(image_bytes)
                    break
                except Exception as exc:
                    logger.warning(
                        f"[image_worker] Attempt {attempt}/{COMFYUI_MAX_RETRIES} failed "
                        f"for prompt #{idx}: {exc}"
                    )
                    if attempt == COMFYUI_MAX_RETRIES:
                        logger.error(
                            f"[image_worker] Giving up on prompt #{idx} after {COMFYUI_MAX_RETRIES} attempts"
                        )
                        failed_count += 1
                        continue
                    time.sleep(2.0 * attempt)

            if image_path and image_path.exists():
                generated.append(str(image_path))

                # Upload to GCS
                theme_slug = job.theme.replace(" ", "_").replace("&", "and")
                gcs_path = f"{GCS_RAW_IMAGES_PREFIX}/{job.date_folder}/{theme_slug}/{image_path.name}"
                try:
                    gcs = self._get_gcs()
                    if gcs:
                        gcs.upload_file(image_path, gcs_path)
                except Exception as exc:
                    logger.warning(
                        f"[image_worker] GCS upload failed for {image_path.name}: {exc}"
                    )

            # Flush progress to Firestore every N images
            if idx % _PROGRESS_FLUSH_EVERY == 0 or idx == total:
                elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
                cost = round(elapsed_hours * GPU_VM_HOURLY_RATE_USD, 4)
                self._push_progress(job, idx, total, cost, gpu_hours=elapsed_hours)
                logger.info(
                    f"[image_worker] Progress: {idx}/{total} images | ${cost:.4f}"
                )

        # Final cost
        elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
        final_cost = round(elapsed_hours * GPU_VM_HOURLY_RATE_USD, 4)

        # Update Job object
        job.generated_images = generated
        stage.cost_usd = final_cost
        stage.gpu_hours = round(elapsed_hours, 4)
        stage.images_done = len(generated)

        if failed_count > 0 and len(generated) == 0:
            stage.mark_failed(f"All {total} prompts failed image generation.")
            raise ImageGenerationError(
                f"Image generation failed for all {total} prompts.", job_id=job.job_id
            )

        stage.mark_completed()
        logger.info(
            f"[image_worker] Done: {len(generated)}/{total} images generated "
            f"| {failed_count} failed | ${final_cost:.4f} USD"
        )
        return job

    # ------------------------------------------------------------------
    # ComfyUI HTTP API
    # ------------------------------------------------------------------

    def _load_workflow(self) -> dict[str, Any]:
        """Load and cache the ComfyUI workflow template JSON.

        Returns:
            Parsed workflow dict (deep copy on use via ``_inject_prompt``).
        """
        if self._workflow_template is not None:
            return self._workflow_template

        workflow_path = Path(self._settings.project_root) / WORKFLOW_JSON_PATH
        if not workflow_path.exists():
            raise ImageGenerationError(
                f"ComfyUI workflow JSON not found at: {workflow_path}. "
                "Expected file: etsy_pipeline/resources/image_z_image_turbo1.json"
            )

        with workflow_path.open("r", encoding="utf-8") as f:
            self._workflow_template = json.load(f)

        logger.info(f"[image_worker] Loaded ComfyUI workflow from {workflow_path}")
        return self._workflow_template  # type: ignore[return-value]

    def _inject_prompt(
        self, workflow: dict[str, Any], prompt_text: str
    ) -> dict[str, Any]:
        """Clone the workflow template and inject a new prompt text and random seed.

        Args:
            workflow: The base workflow template dict.
            prompt_text: The prompt string to inject into the CLIPTextEncode node.

        Returns:
            A new workflow dict with the prompt and seed set.
        """
        import copy

        wf = copy.deepcopy(workflow)
        # Inject prompt text into node 57:27 (CLIPTextEncode)
        wf[WORKFLOW_PROMPT_NODE_ID]["inputs"]["text"] = prompt_text
        # Randomise seed in node 57:3 (KSampler) for variety
        wf[WORKFLOW_SEED_NODE_ID]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
        return wf

    def _submit_prompt(self, workflow: dict[str, Any]) -> str:
        """Submit a workflow to ComfyUI and return the prompt_id.

        Args:
            workflow: The fully configured ComfyUI workflow dict.

        Returns:
            The ``prompt_id`` string assigned by ComfyUI.

        Raises:
            ImageGenerationError: If the HTTP request fails.
        """
        payload = json.dumps({"prompt": workflow}).encode("utf-8")
        req = urllib.request.Request(
            COMFYUI_PROMPT_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
        except Exception as exc:
            raise ImageGenerationError(f"ComfyUI /prompt POST failed: {exc}") from exc

        prompt_id: str = result.get("prompt_id", "")
        if not prompt_id:
            raise ImageGenerationError(
                f"ComfyUI returned no prompt_id. Response: {result}"
            )

        logger.debug(f"[image_worker] Submitted prompt_id={prompt_id}")
        return prompt_id

    def _wait_for_output(self, prompt_id: str) -> tuple[bytes, str]:
        """Poll ComfyUI /history until the prompt is done, then download the image.

        Args:
            prompt_id: The ID returned by ``_submit_prompt``.

        Returns:
            A tuple of (image_bytes, filename).

        Raises:
            ImageGenerationError: If the prompt times out or fails.
        """
        deadline = time.monotonic() + COMFYUI_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                url = f"{COMFYUI_HISTORY_ENDPOINT}/{prompt_id}"
                with urllib.request.urlopen(url, timeout=10) as resp:
                    history = json.loads(resp.read())
            except Exception:
                time.sleep(COMFYUI_POLL_INTERVAL_SECONDS)
                continue

            if prompt_id not in history:
                time.sleep(COMFYUI_POLL_INTERVAL_SECONDS)
                continue

            outputs = history[prompt_id].get("outputs", {})
            save_node_outputs = outputs.get(WORKFLOW_SAVE_NODE_ID, {})
            images = save_node_outputs.get("images", [])

            if not images:
                time.sleep(COMFYUI_POLL_INTERVAL_SECONDS)
                continue

            # Download the first output image
            img_info = images[0]
            filename: str = img_info["filename"]
            subfolder: str = img_info.get("subfolder", "")
            img_type: str = img_info.get("type", "output")

            view_url = (
                f"{COMFYUI_VIEW_ENDPOINT}"
                f"?filename={filename}&subfolder={subfolder}&type={img_type}"
            )
            try:
                with urllib.request.urlopen(view_url, timeout=30) as img_resp:
                    image_bytes = img_resp.read()
            except Exception as exc:
                raise ImageGenerationError(
                    f"Failed to download image {filename}: {exc}"
                ) from exc

            return image_bytes, filename

        raise ImageGenerationError(
            f"Timeout waiting for ComfyUI output for prompt_id={prompt_id} "
            f"after {COMFYUI_TIMEOUT_SECONDS}s"
        )

    # ------------------------------------------------------------------
    # Firestore / GCS helpers
    # ------------------------------------------------------------------

    def _get_gcs(self) -> GCSStore | None:
        """Lazily initialise the GCS store (skipped if GCS_BUCKET is not set)."""
        if self._gcs is not None:
            return self._gcs
        if not self._settings.gcs_bucket:
            logger.warning(
                "[image_worker] GCS_BUCKET not configured — skipping GCS upload"
            )
            return None
        from etsy_pipeline.services.gcs_store import GCSStore

        self._gcs = GCSStore(settings=self._settings)
        return self._gcs

    def _push_progress(
        self,
        job: Job,
        images_done: int,
        images_total: int,
        cost_usd: float,
        gpu_hours: float = 0.0,
    ) -> None:
        """Push live progress to Firestore (no-op if Firestore is not configured)."""
        if self._firestore is None:
            if self._settings.gcp_project_id:
                from etsy_pipeline.services.firestore_store import FirestoreJobStore

                try:
                    self._firestore = FirestoreJobStore(settings=self._settings)
                except Exception as exc:
                    logger.warning(f"[image_worker] Firestore init failed: {exc}")
                    return
            else:
                return

        try:
            self._firestore.update_stage_progress(
                job.job_id,
                self.STAGE_NAME,
                images_done=images_done,
                images_total=images_total,
                cost_usd=cost_usd,
                gpu_hours=gpu_hours,
            )
        except Exception as exc:
            logger.warning(f"[image_worker] Firestore progress push failed: {exc}")
