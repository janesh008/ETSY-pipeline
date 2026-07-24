"""CraftDesk API — 6-Stage Pipeline execution runner and stage retry orchestrator."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

STAGE_DEFINITIONS = [
    {"stage_name": "image_gen", "label": "🎨 Image Generation (ComfyUI)"},
    {"stage_name": "bg_removal", "label": "✂️ Background Removal (rembg)"},
    {"stage_name": "upscaling", "label": "🔍 AI Upscaling (Real-ESRGAN / 4x)"},
    {"stage_name": "mockup_creation", "label": "🖼️ Mockup Creation (etsy mockup creator)"},
    {"stage_name": "pdf_generation", "label": "📄 Clickable PDF Wrap Generation"},
    {"stage_name": "metadata_generation", "label": "📝 Etsy Metadata (300 DPI Description & 13 Tags)"},
]

# In-memory store for pipeline jobs
_PIPELINE_JOBS_STORE: dict[str, dict[str, Any]] = {}


class PipelineRunnerService:
    """Orchestrates 6 pipeline stage execution, failure tracking, and per-stage retry."""

    @classmethod
    def create_job(cls, user_id: str, theme_name: str, prompts: list[str]) -> dict[str, Any]:
        """Initialize a new 6-stage pipeline job."""
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        stages = [
            {
                "stage_name": def_item["stage_name"],
                "label": def_item["label"],
                "status": "pending",
                "progress_percent": 0,
                "error_message": None,
                "stderr_log": None,
                "started_at": None,
                "completed_at": None,
            }
            for def_item in STAGE_DEFINITIONS
        ]

        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "theme_name": theme_name,
            "prompts": prompts or [f"Digital watercolor clipart of {theme_name}"],
            "status": "running",
            "current_stage": "image_gen",
            "stages": stages,
            "hero_image_url": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600",
            "mockups": [
                "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=400",
                "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=400",
                "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=400",
                "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=400",
            ],
            "metadata": {
                "title": f"✨ {theme_name} Watercolor Clipart Bundle — 300 DPI Commercial Use",
                "description": (
                    f"✨ — HOOK — ✨\n"
                    f"Unleash your creative strength with this vibrant {theme_name} clipart set!\n\n"
                    f"📦 — PRODUCT DETAILS — 📦\n"
                    f"- Included Files: 22 high-resolution PNG images (300 DPI, transparent background)\n"
                    f"- Format: Digital Zip Download via PDF link\n"
                    f"- License: Personal & Commercial Use permitted\n"
                ),
                "tags": [
                    theme_name.lower()[:20],
                    "watercolor clipart",
                    "birthday clipart",
                    "png clipart",
                    "sublimation design",
                    "digital download",
                    "commercial use",
                    "print ready 300dpi",
                    "hero clipart",
                    "party graphics",
                    "clipart set",
                    "instant download",
                    "diy craft png",
                ],
            },
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
    async def simulate_stage_execution(cls, job_id: str, stage_name: str, force_fail: bool = False) -> None:
        """Simulate execution of a stage, updating progress percent and handling failure simulation."""
        job = _PIPELINE_JOBS_STORE.get(job_id)
        if not job:
            return

        stage = next((s for s in job["stages"] if s["stage_name"] == stage_name), None)
        if not stage:
            return

        now_str = datetime.now(timezone.utc).isoformat()
        stage["status"] = "running"
        stage["started_at"] = now_str
        stage["progress_percent"] = 10
        stage["error_message"] = None
        stage["stderr_log"] = None
        job["current_stage"] = stage_name

        await asyncio.sleep(0.3)
        stage["progress_percent"] = 50

        if force_fail:
            await asyncio.sleep(0.2)
            stage["status"] = "failed"
            stage["progress_percent"] = 50
            stage["error_message"] = f"RuntimeError in stage [{stage_name}]: Memory limit exceeded or CUDA device timeout."
            stage["stderr_log"] = (
                f"Traceback (most recent call last):\n"
                f'  File "etsy_pipeline/workers/{stage_name}_worker.py", line 42, in run\n'
                f"    result = execute_cuda_pipeline(job)\n"
                f"torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.40 GiB."
            )
            job["status"] = "failed"
            return

        await asyncio.sleep(0.3)
        stage["status"] = "completed"
        stage["progress_percent"] = 100
        stage["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Check if all stages completed
        if all(s["status"] == "completed" for s in job["stages"]):
            job["status"] = "completed"
            job["completed_at"] = datetime.now(timezone.utc)
            job["current_stage"] = None

    @classmethod
    async def run_full_pipeline_async(cls, job_id: str, simulate_fail_stage: str | None = None) -> None:
        """Run all 6 stages sequentially."""
        job = _PIPELINE_JOBS_STORE.get(job_id)
        if not job:
            return

        for stage in job["stages"]:
            s_name = stage["stage_name"]
            should_fail = (s_name == simulate_fail_stage)
            await cls.simulate_stage_execution(job_id, s_name, force_fail=should_fail)
            if should_fail:
                break
