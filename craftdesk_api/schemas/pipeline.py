"""CraftDesk API — Pipeline runner request/response Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class StageStatus(BaseModel):
    """Status of a single pipeline stage."""

    stage_name: str  # "image_gen" | "bg_removal" | "upscaling" | "mockup_creation" | "pdf_generation" | "metadata_generation"
    label: str
    status: str  # "pending" | "running" | "completed" | "failed"
    progress_percent: int = Field(0, ge=0, le=100)
    error_message: str | None = None
    stderr_log: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class PipelineStartRequest(BaseModel):
    """Payload for POST /pipeline/jobs."""

    prompt_job_id: str | None = None
    theme_name: str = Field("Wonder Woman Birthday", min_length=1)
    prompts: list[str] = Field(default_factory=list)


class PipelineJobResponse(BaseModel):
    """Returned when fetching or starting a 6-stage pipeline execution job."""

    job_id: str
    user_id: str
    theme_name: str
    status: str  # "running" | "completed" | "failed"
    current_stage: str | None = None
    stages: list[StageStatus]
    hero_image_url: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
