"""CraftDesk API — Prompt Studio router: Etsy scraper, PromptWorker integration, SKILL.md output, and GCP Bucket save."""

from __future__ import annotations

import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from etsy_pipeline.config.settings import get_settings
from etsy_pipeline.utils.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, Response, status

from craftdesk_api.routers.gcp import get_current_user_id
from craftdesk_api.schemas.prompts import (
    EtsyScrapeRequest,
    EtsyScrapeResponse,
    PromptGenerateRequest,
    PromptGenerateResponse,
    SavePromptToGcpRequest,
    SavePromptToGcpResponse,
    UploadPromptFileRequest,
    UploadPromptFileResponse,
)
from craftdesk_api.services.etsy_scraper import EtsyScraperService
from craftdesk_api.services.prompt_engine import PromptEngineService

router = APIRouter(prefix="/prompts", tags=["prompts"])

logger = get_logger(__name__)

# In-memory store for generated prompt jobs
_PROMPT_JOBS_STORE: dict[str, dict[str, Any]] = {}


def sanitize_slug(text: str) -> str:
    """Sanitize text into a clean character + theme slug (e.g. 'Winnie_The_Pooh_Birthday').

    Removes bullet chars (•), pipes (|), symbols, SEO fluff, and standalone numbers.
    """
    if not text:
        return "Clipart_Set"

    cleaned = text.replace("&", "and")
    cleaned = re.sub(r'[•·∙●|\\/:*?"<>,\.\-\(\)]', " ", cleaned)

    noise_words = {
        "clipart",
        "png",
        "caricature",
        "bundle",
        "graphics",
        "backgrounds",
        "art",
        "illustration",
        "digital",
        "instant",
        "download",
        "svg",
        "eps",
        "design",
        "set",
        "pack",
        "collection",
    }

    tokens = []
    for token in cleaned.split():
        t_lower = token.lower()
        if t_lower in noise_words or token.isdigit():
            continue
        tokens.append(token)

    if not tokens:
        tokens = [t for t in cleaned.split() if not t.isdigit()]
    if not tokens:
        tokens = ["Clipart", "Set"]

    slug = "_".join(tokens[:4])
    return slug[:35].strip("_") or "Clipart_Set"


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
        if (
            not etsy_context
            and body.etsy_url
            and body.etsy_url.strip()
            and body.etsy_url != "string"
        ):
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
            "custom_name": None,
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
    "/upload",
    response_model=UploadPromptFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an uploaded .txt prompt file and return a job_id for use with save-to-gcp",
)
async def upload_prompt_file(
    body: UploadPromptFileRequest,
    user_id: str = Depends(get_current_user_id),
) -> UploadPromptFileResponse:
    """Register raw .txt prompt text in the job store so it can be saved to GCP bucket."""
    job_id = f"upload-{uuid.uuid4().hex[:12]}"
    theme = body.theme.strip() or body.custom_name or "Uploaded_Prompt_File"

    _PROMPT_JOBS_STORE[job_id] = {
        "user_id": user_id,
        "theme": theme,
        "raw_prompt_text": body.raw_prompt_text,
        "prompts": [],
        "sections": {},
        "txt_content": body.raw_prompt_text,
        "etsy_title": None,
        "custom_name": body.custom_name,
    }

    return UploadPromptFileResponse(
        job_id=job_id,
        theme=theme,
        message=f"Prompt file registered as job '{job_id}' — call save-to-gcp to upload to bucket.",
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
    raw_theme = job_data.get("theme", "Clipart_Set")

    # Resolve slug: custom_name from request > custom_name stored in job > auto-slug from theme
    custom_name = (body and body.custom_name) or job_data.get("custom_name") or None
    if custom_name:
        # Sanitize only OS-unsafe chars from user-provided name
        theme_slug = re.sub(r'[\\/:*?"<>|]', "_", custom_name.strip()).strip(
            "_"
        ) or sanitize_slug(raw_theme)
    else:
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

    custom_name = job_data.get("custom_name")
    theme_slug = custom_name if custom_name else sanitize_slug(job_data["theme"])
    filename = f"{theme_slug}.txt"

    return Response(
        content=job_data["raw_prompt_text"],
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/files",
    summary="List all saved prompt files from local Clipart output directory (and GCS if available)",
)
async def list_prompt_files(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return a list of all saved prompt .txt files under output/Clipart/<date>/<theme>/<theme>.txt."""
    settings = get_settings()
    clipart_root = Path(settings.output_root) / "Clipart"

    files: list[dict] = []

    # 1. Scan GCS bucket FIRST (primary source of truth)
    gcs_keys: set[str] = set()
    try:
        from google.cloud import storage as gcs_storage

        bucket_name = (
            settings.gcs_bucket
            or os.getenv("GCP_BUCKET_NAME")
            or "etsy-pixelbar-clipart"
        )
        client = gcs_storage.Client()
        for blob in client.list_blobs(bucket_name, prefix="Clipart/"):
            if not blob.name.endswith(".txt"):
                continue
            gcs_uri = f"gs://{bucket_name}/{blob.name}"
            parts = blob.name.split("/")
            # Expected: Clipart/<date>/<theme>/<filename>.txt  → >=4 parts
            if len(parts) < 4:
                continue
            try:
                date_str = parts[1]
                theme_str = parts[2]
                file_name = Path(blob.name).stem

                content = blob.download_as_text(encoding="utf-8")
                preview_lines = [ln for ln in content.splitlines() if ln.strip()][:4]
                preview = "\n".join(preview_lines)
                prompt_lines = [
                    ln.strip()
                    for ln in content.splitlines()
                    if ln.strip() and not ln.startswith("#")
                ]

                # Check if file also exists on local disk
                local_check = clipart_root / date_str / theme_str / Path(blob.name).name
                local_path_val = str(local_check) if local_check.exists() else None

                gcs_keys.add(f"{date_str}/{theme_str}/{file_name}")
                files.append(
                    {
                        "name": file_name,
                        "date": date_str,
                        "theme": theme_str,
                        "local_path": local_path_val,
                        "gcs_path": gcs_uri,
                        "is_gcs": True,
                        "preview": preview,
                        "prompt_count": len(prompt_lines),
                        "raw_text": content,
                    }
                )
            except Exception:
                continue
    except Exception as exc:
        logger.warning(f"[prompts] GCS bucket prompt list failed: {exc}")

    # 2. Scan local disk output/Clipart/ SECOND for any extra non-GCS files
    if clipart_root.exists():
        for date_dir in sorted(clipart_root.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            for theme_dir in sorted(date_dir.iterdir()):
                if not theme_dir.is_dir():
                    continue
                for txt_file in theme_dir.glob("*.txt"):
                    key = f"{date_dir.name}/{theme_dir.name}/{txt_file.stem}"
                    if key in gcs_keys:
                        continue
                    try:
                        content = txt_file.read_text(encoding="utf-8")
                        preview_lines = [
                            ln for ln in content.splitlines() if ln.strip()
                        ][:4]
                        preview = "\n".join(preview_lines)
                        prompt_lines = [
                            ln.strip()
                            for ln in content.splitlines()
                            if ln.strip() and not ln.startswith("#")
                        ]
                        files.append(
                            {
                                "name": txt_file.stem,
                                "date": date_dir.name,
                                "theme": theme_dir.name,
                                "local_path": str(txt_file),
                                "gcs_path": f"gs://{settings.gcs_bucket or 'etsy-pixelbar-clipart'}/Clipart/{date_dir.name}/{theme_dir.name}/{txt_file.name}",
                                "is_gcs": False,
                                "preview": preview,
                                "prompt_count": len(prompt_lines),
                                "raw_text": content,
                            }
                        )
                    except Exception:
                        continue

    return {"files": files, "total": len(files)}
