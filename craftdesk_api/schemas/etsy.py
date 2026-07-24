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
    is_active: bool
    created_at: datetime
