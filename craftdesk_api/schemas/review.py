"""CraftDesk API — Review Gallery and Etsy Publishing request/response Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewJobResponse(BaseModel):
    """Full review payload containing Hero image, mockup gallery, PDF wrap, and metadata."""

    job_id: str
    theme_name: str
    hero_image_url: str
    mockups: list[str]
    pdf_download_url: str
    title: str
    description: str
    tags: list[str]
    price: float = 5.99
    quantity: int = 999
    status: str  # "READY_FOR_REVIEW" | "PUBLISHED"


class MetadataUpdateRequest(BaseModel):
    """Payload for updating listing title, description, or tags before publishing."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)


class EtsyPushRequest(BaseModel):
    """Payload for publishing a draft listing to a connected Etsy shop."""

    shop_db_id: str = Field(..., description="ID of connected Etsy shop in DB")
    price: float = Field(5.99, gt=0)
    quantity: int = Field(999, ge=1)


class EtsyPushResponse(BaseModel):
    """Returned after creating an Etsy shop draft listing."""

    listing_id: str
    shop_name: str
    etsy_listing_url: str
    status: str = "DRAFT"
    message: str = "Draft listing created successfully on Etsy."
