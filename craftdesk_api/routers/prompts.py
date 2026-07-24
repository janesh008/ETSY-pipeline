"""CraftDesk API — Prompt Studio router: Etsy scraper, multi-input generation, and .txt export."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.db.base import get_db
from craftdesk_api.routers.gcp import get_current_user_id
from craftdesk_api.schemas.prompts import (
    EtsyScrapeRequest,
    EtsyScrapeResponse,
    PromptGenerateRequest,
    PromptGenerateResponse,
)
from craftdesk_api.services.etsy_scraper import EtsyScraperService
from craftdesk_api.services.prompt_engine import PromptEngineService

router = APIRouter(prefix="/prompts", tags=["prompts"])

# In-memory store for generated prompt jobs (Phase 2 will persist to MongoDB)
_PROMPT_JOBS_STORE: dict[str, dict[str, Any]] = {}


@router.post(
    "/scrape-etsy",
    response_model=EtsyScrapeResponse,
    summary="Scrape title, description, and images from an Etsy product URL",
)
async def scrape_etsy_listing(
    body: EtsyScrapeRequest,
    user_id: str = Depends(get_current_user_id),
) -> EtsyScrapeResponse:
    """Extract metadata and thumbnails from a public Etsy product link for style inspiration."""
    try:
        data = await EtsyScraperService.scrape_listing(body.url)
        return EtsyScrapeResponse(
            url=data["url"],
            title=data["title"],
            description=data["description"],
            images=data["images"],
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error scraping Etsy URL: {err!s}",
        )


@router.post(
    "/generate",
    response_model=PromptGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate multi-input AI clipart prompts with Gemini 2.5",
)
async def generate_prompts(
    body: PromptGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PromptGenerateResponse:
    """Generate sectioned clipart prompts using Theme Text, Etsy URL, Reference Images, and Prompt Count."""
    etsy_context = None
    if body.etsy_url:
        try:
            etsy_context = await EtsyScraperService.scrape_listing(body.etsy_url)
        except Exception:
            # Non-fatal — proceed with available inputs
            pass

    result = await PromptEngineService.generate_prompts(
        theme_text=body.theme_text,
        etsy_context=etsy_context,
        reference_images=body.reference_images,
        prompt_count=body.prompt_count,
    )

    job_id = f"prompt-{uuid.uuid4().hex[:12]}"
    theme_name = body.theme_text or (etsy_context.get("title") if etsy_context else "Digital Clipart")

    job_data = {
        "job_id": job_id,
        "user_id": user_id,
        "theme": theme_name,
        "prompts": result["prompts"],
        "txt_content": result["txt_content"],
        "count": result["count"],
        "etsy_title": etsy_context.get("title") if etsy_context else None,
    }

    _PROMPT_JOBS_STORE[job_id] = job_data

    return PromptGenerateResponse(
        job_id=job_id,
        theme=theme_name,
        prompts=result["prompts"],
        txt_content=result["txt_content"],
        count=result["count"],
        etsy_title=etsy_context.get("title") if etsy_context else None,
    )


@router.get(
    "/jobs/{job_id}/export",
    summary="Download prompt set as plain text (.txt) file",
)
async def export_prompts_txt(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> Response:
    """Download the generated prompt set matrix as a plain text (.txt) file."""
    job = _PROMPT_JOBS_STORE.get(job_id)
    if not job or job.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt job not found or access denied.",
        )

    txt_content = job["txt_content"]
    safe_theme = "".join(c if c.isalnum() else "_" for c in job["theme"])[:30]
    filename = f"CraftDesk_Prompts_{safe_theme}_{job_id}.txt"

    return Response(
        content=txt_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
