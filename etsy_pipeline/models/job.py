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

    def mark_running(self, worker_id: str | None = None) -> None:
        """Mark this stage as running."""
        self.status = StageStatus.RUNNING
        self.started_at = datetime.now(UTC)
        self.worker_id = worker_id

    def mark_completed(self) -> None:
        """Mark this stage as completed."""
        self.status = StageStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

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
    theme: str = Field(..., description="Cartoon/character theme name (e.g., 'Lilo & Stitch')")
    event_type: str = Field(default="Normal", description="Event theme (e.g., 'birthday', 'baby shower')")
    style_hint: str | None = Field(default=None, description="Optional style override (e.g., 'watercolor', '3D')")
    prompt_count: int | None = Field(default=None, description="Optional total prompt count override")
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

    # Metadata Generation
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Etsy listing metadata (title, description, tags)",
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
    errors: list[str] = Field(default_factory=list, description="Accumulated error messages")
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

    def get_output_dir(self, output_root: str | Path) -> Path:
        """Get the output directory for this job."""
        return Path(output_root) / self.date_folder / self.theme.replace(" ", "_").replace("&", "and")

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
        ]
        return "\n".join(lines)
