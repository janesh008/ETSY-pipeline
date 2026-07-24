"""CraftDesk API — auth request/response Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    """Returned after a successful registration."""

    user_id: str
    email: str
    full_name: str
    message: str = "Account created successfully."


# ── Login ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token pair returned on login or refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Refresh ──────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh."""

    refresh_token: str


# ── Me ────────────────────────────────────────────────────────────────────────

class UserMeResponse(BaseModel):
    """Current authenticated user profile."""

    user_id: str
    email: str
    full_name: str
