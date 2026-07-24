"""CraftDesk API — User Settings and API Keys request/response Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfileUpdate(BaseModel):
    """Payload for updating user profile info."""

    full_name: str = Field(..., min_length=1, max_length=255)


class ApiKeySave(BaseModel):
    """Payload for saving an external API key (Gemini, Replicate)."""

    service: str = Field(..., description="Service identifier e.g. 'gemini' or 'replicate'")
    api_key: str = Field(..., min_length=1, description="Raw third-party API key")


class ApiKeyResponse(BaseModel):
    """Saved API key metadata (raw key hidden)."""

    id: str
    service: str
    has_key: bool = True
