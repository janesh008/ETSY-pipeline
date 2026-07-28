"""CraftDesk API — Prompt Studio request/response Pydantic schemas."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class EtsyScrapeRequest(BaseModel):
    """Payload for POST /prompts/scrape-etsy."""

    url: str = Field(..., description="Public Etsy product listing URL")


class EtsyScrapeResponse(BaseModel):
    """Result of Etsy listing web scrape or OpenAPI v3 fetch."""

    url: str
    title: str
    description: str
    images: list[str]
    tags: list[str] = Field(default_factory=list)


class PromptGenerateRequest(BaseModel):
    """Payload for POST /prompts/generate."""

    theme_text: str = Field("", description="Optional text theme e.g. Wonder Woman Birthday Watercolor")
    etsy_url: str | None = Field(None, description="Optional Etsy listing URL to scrape context from")
    scraped_context: dict[str, Any] | None = Field(None, description="Optional scraped market context (title, description, tags)")
    reference_images: list[str] = Field(default_factory=list, description="Optional reference image URLs or base64 strings")
    prompt_count: int = Field(22, ge=1, le=150, description="Target number of clipart prompts to generate (1-150)")


class PromptGenerateResponse(BaseModel):
    """Returned after multi-input prompt generation from PromptWorker."""

    job_id: str
    theme: str
    raw_prompt_text: str = Field(..., description="Unparsed SKILL.md output text with locked section headings ## SECTION_NAME")
    prompts: list[str] = Field(default_factory=list)
    sections: dict[str, list[str]] = Field(default_factory=dict, description="Parsed section map (e.g. {'MAIN_CHARACTER': [...], 'SCENE': [...]})")
    txt_content: str
    count: int
    etsy_title: str | None = None


class UploadPromptFileRequest(BaseModel):
    """Payload for POST /prompts/upload — registers raw .txt prompt text and returns a job_id."""

    raw_prompt_text: str = Field(..., description="Raw prompt file text content")
    theme: str = Field("", description="Optional theme / character name used to derive the filename")
    custom_name: str | None = Field(None, description="Optional custom filename override (without extension)")


class UploadPromptFileResponse(BaseModel):
    """Response after uploading an existing prompt file."""

    job_id: str
    theme: str
    message: str


class SavePromptToGcpRequest(BaseModel):
    """Payload to save prompt set to GCP Storage Bucket."""

    bucket_name: str | None = Field(None, description="Optional GCP Storage bucket name override")
    custom_name: str | None = Field(None, description="Optional custom filename override (without extension)")


class SavePromptToGcpResponse(BaseModel):
    """Response after saving prompt file to GCP bucket."""

    job_id: str
    gcs_path: str
    status: str
    message: str
