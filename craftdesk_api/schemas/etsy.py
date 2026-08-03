"""CraftDesk API — Etsy Shop Connector request/response Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EtsyAuthUrlRequest(BaseModel):
    """Payload for GET /etsy/auth/url query params."""

    redirect_uri: str = Field(..., description="OAuth callback redirect URL")


class EtsyAuthUrlResponse(BaseModel):
    """Returned when initiating Etsy OAuth 2.0 PKCE consent flow."""

    auth_url: str
    state: str
    code_verifier: str


class EtsyCallbackRequest(BaseModel):
    """Payload for POST /etsy/auth/callback."""

    code: str = Field(..., description="Authorization code returned by Etsy callback")
    code_verifier: str = Field(..., description="PKCE verifier generated in step 1")
    redirect_uri: str = Field(..., description="Redirect URI passed in step 1")


class EtsyShopResponse(BaseModel):
    """Connected Etsy shop details (tokens hidden)."""

    id: str
    shop_id: str
    shop_name: str
    slug: str = Field(default="", description="URL-safe shop slug")
    is_active: bool
    created_at: datetime



class EtsyShopUpdateRequest(BaseModel):
    """Payload for updating shop details (e.g. shop_name)."""

    shop_name: str = Field(..., min_length=1, max_length=255, description="Updated shop display name")


class EtsyShopCreateRequest(BaseModel):
    """Payload for manually adding a shop."""

    shop_name: str = Field(..., min_length=1, max_length=255, description="Shop display name")
    shop_id: str | None = Field(default=None, description="Optional custom shop ID")


class EtsyShopStatsResponse(BaseModel):
    """Live shop metrics and connection verification details fetched from Etsy API v3."""

    is_connected: bool = Field(default=True)
    shop_id: str
    shop_name: str
    active_listings_count: int = Field(default=0)
    digital_listings_count: int = Field(default=0)
    review_count: int = Field(default=0)
    review_average: float = Field(default=5.0)
    currency_code: str = Field(default="USD")
    etsy_url: str = Field(default="")
    message: str = Field(default="Verified live via Etsy API v3")




# ── Listing Upload & Publish Schemas ─────────────────────────────────────


class GcsFolderItem(BaseModel):
    """Represents a clipart theme folder found in GCS bucket."""

    gcs_prefix: str = Field(..., description="GCS prefix, e.g. 'Clipart/2026-07-22/Wonder_Woman/'")
    date_folder: str = Field(..., description="Folder date, e.g. '2026-07-22'")
    theme_slug: str = Field(..., description="Theme slug identifier")
    display_name: str = Field(..., description="Human-readable theme display name")
    has_mockups: bool = Field(default=False)
    has_pdf: bool = Field(default=False)
    has_metadata: bool = Field(default=False, description="True if metadata/listing.json exists")


class GcsFolderListResponse(BaseModel):
    """List of GCS clipart folders available for listing upload."""

    folders: list[GcsFolderItem] = Field(default_factory=list)
    gcs_available: bool = Field(default=True)


class GcsFolderDetailsResponse(BaseModel):
    """Full details, metadata, and mockup file list for a specific GCS clipart theme folder."""

    gcs_prefix: str
    theme_slug: str
    display_name: str
    date_folder: str
    title: str = Field(default="")
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    price: float = Field(default=5.99)
    quantity: int = Field(default=999)
    who_made: str = Field(default="i_did")
    is_ai_created: bool = Field(default=True)
    renewal_option: str = Field(default="automatic")
    taxonomy_id: int = Field(default=6844)
    craft_type: list[str] = Field(
        default_factory=lambda: ["Card making & stationery", "Collage", "Kids' crafts"]
    )
    mockups: list[str] = Field(default_factory=list, description="List of mockup image filenames or relative keys")




class GcsListingRequest(BaseModel):
    """Request payload for publishing an Etsy listing from a GCS folder."""

    gcs_prefix: str = Field(..., description="Target GCS folder prefix")
    title: str | None = Field(default=None, description="Title override (max 140 chars)")
    description: str | None = Field(default=None, description="Description override")
    tags: list[str] = Field(default_factory=list, description="Tags override (max 13 tags, 20 chars max each)")
    price: float = Field(default=5.99, ge=0.20, description="Listing price USD")
    quantity: int = Field(default=999, ge=1, description="Stock quantity")
    is_ai_created: bool | None = Field(default=None, description="Whether listing is AI created")
    renewal_option: str | None = Field(default=None, description="Etsy renewal option ('automatic' or 'manual')")


class GenerateMetadataResponse(BaseModel):
    """Response returned after generating metadata from uploaded mockup images."""

    title: str
    description: str
    tags: list[str]


class ListingPublishResponse(BaseModel):
    """Result of publishing a listing to Etsy."""

    listing_id: str
    etsy_listing_url: str
    status: str = Field(default="active", description="'active' or 'draft'")
    shop_name: str
    images_uploaded: int
    pdf_uploaded: bool
    message: str

