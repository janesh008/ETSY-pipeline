"""CraftDesk API — Review Gallery and Etsy Publishing router."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.core.security import decrypt
from craftdesk_api.db.base import get_db
from craftdesk_api.models.etsy_shop import EtsyShop
from craftdesk_api.routers.gcp import get_current_user_id
from craftdesk_api.schemas.review import (
    EtsyPushRequest,
    EtsyPushResponse,
    MetadataUpdateRequest,
    ReviewJobResponse,
)
from craftdesk_api.services.etsy_publisher import EtsyPublisherService
from craftdesk_api.services.pipeline_runner import PipelineRunnerService

router = APIRouter(prefix="/review", tags=["review"])


def _format_media_url(path: str) -> str:
    """Format local file path to proxy endpoint URL for frontend preview."""
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    # If path starts with output/ or is a relative path in output dir
    normalized = path.replace("\\", "/")

    from etsy_pipeline.services.gcs_store import is_gcp_available

    if is_gcp_available():
        gcs_key = normalized
        if gcs_key.startswith("output/"):
            gcs_key = "Clipart/" + gcs_key[len("output/") :]
        return f"/api/v1/etsy/gcs-media?object_key={gcs_key}"

    return f"/api/v1/review/media?path={normalized}"


def _build_review_response(job: dict[str, Any]) -> ReviewJobResponse:
    """Build ReviewJobResponse mapping local file paths to proxy media URLs."""
    meta = job.get("metadata", {})
    raw_mockups = job.get("mockups") or []

    mockups = [_format_media_url(m) for m in raw_mockups]
    if not mockups:
        # Fallback list of placeholders
        mockups = [
            "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600",
            "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=600",
            "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=600",
            "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600",
        ]

    raw_hero = job.get("hero_image_url")
    hero = _format_media_url(raw_hero) if raw_hero else mockups[0]

    pdf_url = (
        job.get("pdf_drive_link")
        or f"https://drive.google.com/file/d/demo-pdf-{job['job_id']}/view"
    )

    return ReviewJobResponse(
        job_id=job["job_id"],
        theme_name=job["theme_name"],
        hero_image_url=hero,
        mockups=mockups,
        pdf_download_url=pdf_url,
        title=meta.get("title", f"✨ {job['theme_name']} Watercolor Clipart Set"),
        description=meta.get(
            "description",
            "High-resolution digital watercolor clipart bundle for commercial use.",
        ),
        tags=meta.get("tags", ["watercolor clipart", "digital download", "craft png"]),
        price=5.99,
        quantity=999,
        status="READY_FOR_REVIEW",
    )


@router.get(
    "/media",
    summary="Serve local mockup or PDF files from output directory",
)
async def serve_local_media(
    path: str,
    user_id: str = Depends(get_current_user_id),
) -> FileResponse:
    """Serve a local file from the output directory for preview/lightbox."""
    normalized = path.replace("\\", "/")

    # Prevent directory traversal attacks
    if ".." in normalized or not normalized.startswith("output/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: path must be inside the output directory.",
        )

    file_path = Path(normalized)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}",
        )

    return FileResponse(file_path)


@router.get(
    "/{job_id}",
    response_model=ReviewJobResponse,
    summary="Get full mockup gallery, PDF wrap link, and metadata for review",
)
async def get_job_review_data(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ReviewJobResponse:
    """Fetch complete review payload: Hero image, ALL mockups, PDF download link, title, description, and tags."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        # Provide demo job payload if user views demo job
        job = PipelineRunnerService.create_job(
            user_id, "Wonder Woman Birthday Watercolor", []
        )

    return _build_review_response(job)


@router.put(
    "/{job_id}/metadata",
    response_model=ReviewJobResponse,
    summary="Update listing title, description, or tags before publishing",
)
async def update_job_metadata(
    job_id: str,
    body: MetadataUpdateRequest,
    user_id: str = Depends(get_current_user_id),
) -> ReviewJobResponse:
    """Save inline edits to listing title, description, or tags."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline job not found.",
        )

    job["metadata"]["title"] = body.title
    job["metadata"]["description"] = body.description
    job["metadata"]["tags"] = body.tags

    return _build_review_response(job)


@router.post(
    "/{job_id}/push-to-etsy",
    response_model=EtsyPushResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Push generated listing to connected Etsy shop as a Draft listing",
)
async def push_to_etsy_shop(
    job_id: str,
    body: EtsyPushRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> EtsyPushResponse:
    """Publish generated clipart bundle directly to selected Etsy shop as a Draft listing."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        # Fallback for demo job
        job = PipelineRunnerService.create_job(
            user_id, "Wonder Woman Birthday Watercolor", []
        )

    # Fetch shop connection from DB
    result = await db.execute(
        select(EtsyShop).where(
            EtsyShop.id == body.shop_db_id, EtsyShop.user_id == user_id
        )
    )
    shop_row = result.scalar_one_or_none()
    if not shop_row:
        # If shop_db_id is demo string, mock shop details
        shop_id = "66082828"
        shop_name = "PixelBarStudio"
        access_token = "demo-access-token"
    else:
        shop_id = shop_row.shop_id
        shop_name = shop_row.shop_name
        access_token = decrypt(shop_row.encrypted_access_token)

    meta = job.get("metadata", {})
    title = meta.get("title", f"{job['theme_name']} Clipart Set")
    description = meta.get(
        "description", "Watercolor clipart bundle for commercial use."
    )
    tags = meta.get("tags", ["watercolor clipart", "digital download"])

    pub_result = await EtsyPublisherService.create_draft_listing(
        shop_id=shop_id,
        access_token=access_token,
        title=title,
        description=description,
        tags=tags,
        price=body.price,
        quantity=body.quantity,
    )

    return EtsyPushResponse(
        listing_id=pub_result["listing_id"],
        shop_name=shop_name,
        etsy_listing_url=pub_result["etsy_listing_url"],
        status="DRAFT",
        message=f"Draft listing '{title[:30]}...' successfully pushed to Etsy shop '{shop_name}'! 🎉",
    )
