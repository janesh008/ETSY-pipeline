"""CraftDesk API — Review Gallery and Etsy Publishing router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
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
        job = PipelineRunnerService.create_job(user_id, "Wonder Woman Birthday Watercolor", [])

    meta = job.get("metadata", {})
    return ReviewJobResponse(
        job_id=job["job_id"],
        theme_name=job["theme_name"],
        hero_image_url=job["hero_image_url"],
        mockups=job.get("mockups", []),
        pdf_download_url=f"https://drive.google.com/file/d/demo-pdf-{job['job_id']}/view",
        title=meta.get("title", f"✨ {job['theme_name']} Watercolor Clipart Set"),
        description=meta.get("description", "High-resolution digital watercolor clipart bundle for commercial use."),
        tags=meta.get("tags", ["watercolor clipart", "digital download", "craft png"]),
        price=5.99,
        quantity=999,
        status="READY_FOR_REVIEW",
    )


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

    meta = job["metadata"]
    return ReviewJobResponse(
        job_id=job["job_id"],
        theme_name=job["theme_name"],
        hero_image_url=job["hero_image_url"],
        mockups=job.get("mockups", []),
        pdf_download_url=f"https://drive.google.com/file/d/demo-pdf-{job['job_id']}/view",
        title=meta["title"],
        description=meta["description"],
        tags=meta["tags"],
        price=5.99,
        quantity=999,
        status="READY_FOR_REVIEW",
    )


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
        job = PipelineRunnerService.create_job(user_id, "Wonder Woman Birthday Watercolor", [])

    # Fetch shop connection from DB
    result = await db.execute(
        select(EtsyShop).where(EtsyShop.id == body.shop_db_id, EtsyShop.user_id == user_id)
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
    description = meta.get("description", "Watercolor clipart bundle for commercial use.")
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
