"""
Job model — the shared state object passed between all pipeline stages.

The Job model stores everything needed across the pipeline: theme info,
generated prompts, image paths, metadata, logs, and execution timestamps.
No global variables — all state lives here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """Status of a pipeline job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"


class StageStatus(StrEnum):
    """Status of an individual pipeline stage within a job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class StageResult(BaseModel):
    """Result of a single pipeline stage execution."""

    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    worker_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- Cost & Progress Tracking ---
    cost_usd: float = Field(
        default=0.0,
        description="Estimated USD cost incurred by this stage (GPU time, API calls, etc.)",
    )
    # Image generation progress (used by image_worker)
    images_total: int = Field(
        default=0,
        description="Total number of images to generate in this stage",
    )
    images_done: int = Field(
        default=0,
        description="Number of images completed so far in this stage",
    )
    gpu_hours: float = Field(
        default=0.0,
        description="GPU compute hours consumed by this stage",
    )

    def mark_running(self, worker_id: str | None = None) -> None:
        """Mark this stage as running."""
        self.status = StageStatus.RUNNING
        self.started_at = datetime.now(UTC)
        self.worker_id = worker_id

    def mark_completed(
        self,
        cost_usd: float | None = None,
        images_done: int | None = None,
        images_total: int | None = None,
        gpu_hours: float | None = None,
    ) -> None:
        """Mark this stage as completed."""
        self.status = StageStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        if cost_usd is not None:
            self.cost_usd = cost_usd
        if images_done is not None:
            self.images_done = images_done
        if images_total is not None:
            self.images_total = images_total
        if gpu_hours is not None:
            self.gpu_hours = gpu_hours

    def mark_failed(self, error_message: str) -> None:
        """Mark this stage as failed with an error message."""
        self.status = StageStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.error_message = error_message

    @property
    def duration_seconds(self) -> float | None:
        """Calculate duration in seconds, if both timestamps exist."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def progress_pct(self) -> float | None:
        """Image generation progress as a 0.0–100.0 percentage, or None if not applicable."""
        if self.images_total > 0:
            return round(self.images_done / self.images_total * 100, 1)
        return None


class Job(BaseModel):
    """
    Central state object passed between all pipeline stages.

    Every module receives a Job, operates on it, and returns it.
    No module should directly call another module — the Pipeline
    orchestrator handles sequencing.

    Example usage:
        job = Job(theme="Lilo & Stitch", event_type="birthday")
        job = pipeline.run(job)
    """

    # --- Identity ---
    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    date_folder: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d")
    )

    # --- Input Parameters ---
    theme: str = Field(
        ..., description="Cartoon/character theme name (e.g., 'Lilo & Stitch')"
    )
    event_type: str = Field(
        default="Normal", description="Event theme (e.g., 'birthday', 'baby shower')"
    )
    style_hint: str | None = Field(
        default=None, description="Optional style override (e.g., 'watercolor', '3D')"
    )
    prompt_count: int | None = Field(
        default=None, description="Optional total prompt count override"
    )
    sections_requested: list[str] | None = Field(
        default=None,
        description="Optional list of specific sections to generate (default = full bundle)",
    )

    # --- Stage Outputs ---
    # Prompt Generation
    prompts: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Section name -> list of prompt strings (e.g., {'MAIN_CHARACTER': [...], 'PATTERN': [...]})",
    )
    raw_prompt_text: str | None = Field(
        default=None,
        description="Raw text response from Gemini before parsing",
    )
    character_roster: dict[str, str] = Field(
        default_factory=dict,
        description="Character slot -> description (e.g., {'MAIN_CHARACTER': 'Stitch — blue alien'})",
    )

    # Image Generation
    generated_images: list[str] = Field(
        default_factory=list,
        description="Paths to generated images from ComfyUI",
    )

    # Background Removal
    bg_removed_images: list[str] = Field(
        default_factory=list,
        description="Paths to background-removed images",
    )

    # Upscaling
    upscaled_images: list[str] = Field(
        default_factory=list,
        description="Paths to upscaled images",
    )

    # Mockup Generation
    mockups: list[str] = Field(
        default_factory=list,
        description="Paths to generated mockup images",
    )
    pdf_path: str | None = Field(
        default=None,
        description="Local path to the generated clickable PDF wrapper",
    )
    pdf_drive_link: str | None = Field(
        default=None,
        description="Public Google Drive link for the upscaled clipart files",
    )

    # Metadata Generation
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Etsy listing metadata (title, description, tags)",
    )
    etsy_title: str | None = Field(
        default=None,
        description="Etsy listing title (max 140 chars)",
    )
    etsy_description: str | None = Field(
        default=None,
        description="Etsy listing full description text",
    )
    etsy_tags: list[str] = Field(
        default_factory=list,
        description="List of 13 Etsy listing tags (max 20 chars each)",
    )
    listing_price_usd: float = Field(
        default=3.99,
        description="Etsy listing price in USD",
    )
    listing_quantity: int = Field(
        default=999,
        description="Etsy listing stock quantity",
    )
    etsy_listing_id: str | None = Field(
        default=None,
        description="Etsy listing ID generated after live upload",
    )
    etsy_listing_url: str | None = Field(
        default=None,
        description="Public Etsy listing URL after live upload",
    )

    # CSV Generation
    csv_path: str | None = Field(
        default=None,
        description="Path to the generated CSV file for Etsy upload",
    )

    # --- Execution State ---
    status: JobStatus = JobStatus.PENDING
    stages: dict[str, StageResult] = Field(
        default_factory=lambda: {
            "prompt_generation": StageResult(),
            "image_generation": StageResult(),
            "bg_removal": StageResult(),
            "upscaling": StageResult(),
            "mockups": StageResult(),
            "metadata_generation": StageResult(),
            "csv_generation": StageResult(),
            "etsy_upload": StageResult(),
        }
    )
    errors: list[str] = Field(
        default_factory=list, description="Accumulated error messages"
    )
    logs: list[str] = Field(default_factory=list, description="Execution log entries")

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # --- Configuration Overrides ---
    config_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-job configuration overrides (e.g., different model, output path)",
    )

    def add_log(self, message: str) -> None:
        """Append a timestamped log entry."""
        timestamp = datetime.now(UTC).isoformat()
        self.logs.append(f"[{timestamp}] {message}")
        self.updated_at = datetime.now(UTC)

    def add_error(self, error: str) -> None:
        """Record an error message."""
        self.errors.append(error)
        self.add_log(f"ERROR: {error}")

    @property
    def total_prompt_count(self) -> int:
        """Total number of prompts across all sections."""
        return sum(len(prompts) for prompts in self.prompts.values())

    @property
    def active_sections(self) -> list[str]:
        """List of sections that have at least one prompt."""
        return [section for section, prompts in self.prompts.items() if prompts]

    @property
    def theme_slug(self) -> str:
        """URL and filesystem-safe theme identifier (e.g. 'Lilo_and_Stitch')."""
        return self.theme.replace(" ", "_").replace("&", "and")

    def get_output_dir(self, output_root: str | Path) -> Path:
        """Get the output directory for this job."""
        return Path(output_root) / self.date_folder / self.theme_slug

    @property
    def total_cost_usd(self) -> float:
        """Total estimated USD cost across all pipeline stages."""
        return round(sum(s.cost_usd for s in self.stages.values()), 4)

    def to_summary(self) -> str:
        """Generate a human-readable summary of the job state."""
        lines = [
            f"Job: {self.job_id}",
            f"Theme: {self.theme} ({self.event_type})",
            f"Status: {self.status}",
            f"Created: {self.created_at.isoformat()}",
            f"Prompts: {self.total_prompt_count} across {len(self.active_sections)} sections",
            f"Images: {len(self.generated_images)} generated, {len(self.bg_removed_images)} bg-removed, {len(self.upscaled_images)} upscaled",
            f"Mockups: {len(self.mockups)}",
            f"Errors: {len(self.errors)}",
            f"Total Cost: ${self.total_cost_usd:.4f} USD",
        ]
        # Per-stage cost breakdown
        stage_lines = []
        for stage_name, stage in self.stages.items():
            if stage.cost_usd > 0 or stage.status not in (
                StageStatus.PENDING,
                StageStatus.SKIPPED,
            ):
                progress = (
                    f" ({stage.images_done}/{stage.images_total})"
                    if stage.images_total > 0
                    else ""
                )
                stage_lines.append(
                    f"  {stage_name}: {stage.status}{progress} | ${stage.cost_usd:.4f}"
                )
        if stage_lines:
            lines.append("\nStage Costs:")
            lines.extend(stage_lines)
        return "\n".join(lines)
