"""CraftDesk API — Prompt Studio router: Etsy scraper, PromptWorker integration, SKILL.md output, and GCP Bucket save."""
from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from craftdesk_api.routers.gcp import get_current_user_id
from craftdesk_api.schemas.prompts import (
    EtsyScrapeRequest,
    EtsyScrapeResponse,
    PromptGenerateRequest,
    PromptGenerateResponse,
    SavePromptToGcpRequest,
    SavePromptToGcpResponse,
)
from craftdesk_api.services.etsy_scraper import EtsyScraperService
from craftdesk_api.services.prompt_engine import PromptEngineService
from etsy_pipeline.config.settings import get_settings

router = APIRouter(prefix="/prompts", tags=["prompts"])

# In-memory store for generated prompt jobs
_PROMPT_JOBS_STORE: dict[str, dict[str, Any]] = {}


def sanitize_slug(text: str) -> str:
    """Sanitize text into a clean, filesystem-safe and GCP-safe slug (removing invalid Windows chars like |, :, ?, *, etc.)."""
    if not text:
        return "Clipart_Set"
    cleaned = text.replace("&", "and")
    cleaned = re.sub(r'[\\/:*?"<>|,\.\-\(\)]', " ", cleaned)
    cleaned = re.sub(r'[\s_]+', "_", cleaned).strip("_")
    return cleaned[:50] or "Clipart_Set"


@router.post(
    "/scrape-etsy",
    response_model=EtsyScrapeResponse,
    summary="Scrape title, description, tags, and images from an Etsy product URL",
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
            tags=data.get("tags", []),
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
    summary="Synthesize AI prompt matrix using etsy_pipeline PromptWorker & SKILL.md rules",
)
async def generate_prompts(
    body: PromptGenerateRequest,
    user_id: str = Depends(get_current_user_id),
) -> PromptGenerateResponse:
    """Run etsy_pipeline PromptWorker to output exact SKILL.md section-structured prompt set."""
    try:
        etsy_context: dict[str, Any] | None = body.scraped_context
        if not etsy_context and body.etsy_url and body.etsy_url.strip() and body.etsy_url != "string":
            try:
                etsy_context = await EtsyScraperService.scrape_listing(body.etsy_url)
            except Exception:
                pass

        result = await PromptEngineService.generate_prompts(
            theme_text=body.theme_text,
            etsy_context=etsy_context,
            reference_images=body.reference_images,
            prompt_count=body.prompt_count,
        )

        job_id = result.get("job_id") or f"job-{uuid.uuid4().hex[:12]}"
        etsy_title = etsy_context.get("title") if etsy_context else None

        _PROMPT_JOBS_STORE[job_id] = {
            "user_id": user_id,
            "theme": result["theme"],
            "raw_prompt_text": result["raw_prompt_text"],
            "prompts": result["prompts"],
            "sections": result.get("sections", {}),
            "txt_content": result["txt_content"],
            "etsy_title": etsy_title,
        }

        return PromptGenerateResponse(
            job_id=job_id,
            theme=result["theme"],
            raw_prompt_text=result["raw_prompt_text"],
            prompts=result["prompts"],
            sections=result.get("sections", {}),
            txt_content=result["txt_content"],
            count=result["count"],
            etsy_title=etsy_title,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate prompts: {err!s}",
        )


@router.post(
    "/jobs/{job_id}/save-to-gcp",
    response_model=SavePromptToGcpResponse,
    summary="Save exact SKILL.md prompt file to GCP Cloud Storage Bucket & prepare for ImageWorker",
)
async def save_prompt_to_gcp(
    job_id: str,
    body: SavePromptToGcpRequest | None = None,
    user_id: str = Depends(get_current_user_id),
) -> SavePromptToGcpResponse:
    """Save prompt set in exact Clipart/<date>/<theme_slug>/<theme_slug>.txt format locally and to GCS."""
    job_data = _PROMPT_JOBS_STORE.get(job_id)
    if not job_data or job_data["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt job not found.",
        )

    settings = get_settings()
    bucket_name = (
        (body and body.bucket_name)
        or settings.gcs_bucket
        or os.getenv("GCP_BUCKET_NAME")
        or "etsy-pipeline-bucket"
    )

    date_folder = datetime.now(UTC).strftime("%Y-%m-%d")
    raw_theme = job_data.get("theme", "Wonder_Woman")
    theme_slug = sanitize_slug(raw_theme)

    # 1. Exact local path: output/Clipart/<date>/<theme_slug>/<theme_slug>.txt
    clipart_dir = Path(settings.output_root) / "Clipart" / date_folder / theme_slug
    clipart_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = clipart_dir / f"{theme_slug}.txt"
    prompt_file.write_text(job_data["raw_prompt_text"], encoding="utf-8")

    # 2. Upload to GCP Storage Bucket: gs://<bucket_name>/Clipart/<date>/<theme_slug>/<theme_slug>.txt
    gcs_blob_path = f"Clipart/{date_folder}/{theme_slug}/{theme_slug}.txt"
    gcs_uri = f"gs://{bucket_name}/{gcs_blob_path}"

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_path)
        blob.upload_from_string(
            job_data["raw_prompt_text"], content_type="text/plain; charset=utf-8"
        )
        status_msg = "SUCCESS"
        msg = f"Saved SKILL.md prompt set to GCP Bucket '{gcs_uri}' and local file '{prompt_file}'."
    except Exception as err:
        status_msg = "SAVED_LOCALLY"
        msg = f"Saved SKILL.md prompt set locally to '{prompt_file}'. (GCP Storage notice: {err!s})"

    return SavePromptToGcpResponse(
        job_id=job_id,
        gcs_path=gcs_uri,
        status=status_msg,
        message=msg,
    )


@router.get(
    "/jobs/{job_id}/export",
    summary="Download generated prompt matrix as a .txt file",
)
async def export_prompts_txt(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> Response:
    """Download prompt set as plain text attachment."""
    job_data = _PROMPT_JOBS_STORE.get(job_id)
    if not job_data or job_data["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt job not found.",
        )

    theme_slug = sanitize_slug(job_data["theme"])
    filename = f"CraftDesk_SKILL_Prompts_{theme_slug}.txt"

    return Response(
        content=job_data["raw_prompt_text"],
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
