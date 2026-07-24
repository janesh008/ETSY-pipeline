"""CraftDesk API — Prompt Studio request/response Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EtsyScrapeRequest(BaseModel):
    """Payload for POST /prompts/scrape-etsy."""

    url: str = Field(..., description="Public Etsy product listing URL")


class EtsyScrapeResponse(BaseModel):
    """Result of Etsy listing web scrape."""

    url: str
    title: str
    description: str
    images: list[str]


class PromptGenerateRequest(BaseModel):
    """Payload for POST /prompts/generate."""

    theme_text: str = Field("", description="Optional text theme e.g. Wonder Woman Birthday")
    etsy_url: str | None = Field(None, description="Optional Etsy listing URL to scrape context from")
    reference_images: list[str] = Field(default_factory=list, description="Optional reference image URLs or base64 strings")
    prompt_count: int = Field(22, ge=1, le=100, description="Target number of clipart prompts to generate")


class PromptGenerateResponse(BaseModel):
    """Returned after multi-input prompt generation."""

    job_id: str
    theme: str
    prompts: list[str]
    txt_content: str
    count: int
    etsy_title: str | None = None
