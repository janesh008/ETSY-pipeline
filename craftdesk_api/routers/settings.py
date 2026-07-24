"""CraftDesk API — User profile and encrypted API Keys router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.core.security import encrypt
from craftdesk_api.db.base import get_db
from craftdesk_api.models.api_key import ApiKey
from craftdesk_api.models.user import User
from craftdesk_api.routers.gcp import get_current_user_id
from craftdesk_api.schemas.auth import UserMeResponse
from craftdesk_api.schemas.settings import (
    ApiKeyResponse,
    ApiKeySave,
    UserProfileUpdate,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.put(
    "/profile",
    response_model=UserMeResponse,
    summary="Update user full name / profile metadata",
)
async def update_profile(
    body: UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserMeResponse:
    """Update profile information for the authenticated user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user_row = result.scalar_one_or_none()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    user_row.full_name = body.full_name
    await db.flush()

    return UserMeResponse(
        user_id=user_row.id,
        email=user_row.email,
        full_name=user_row.full_name,
    )


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save AES-256 Fernet encrypted external API key (Gemini, Replicate)",
)
async def save_api_key(
    body: ApiKeySave,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """Encrypt and store an API key for Gemini or Replicate services."""
    service_clean = body.service.lower().strip()
    encrypted_key = encrypt(body.api_key)

    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.service == service_clean)
    )
    existing_key = result.scalar_one_or_none()

    if existing_key:
        existing_key.encrypted_api_key = encrypted_key
        key_row = existing_key
    else:
        key_row = ApiKey(
            user_id=user_id,
            service=service_clean,
            encrypted_api_key=encrypted_key,
        )
        db.add(key_row)

    await db.flush()

    return ApiKeyResponse(
        id=key_row.id,
        service=key_row.service,
        has_key=True,
    )


@router.get(
    "/api-keys",
    response_model=list[ApiKeyResponse],
    summary="List saved API keys metadata (raw keys hidden)",
)
async def list_api_keys(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """Fetch saved API key services for current user."""
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == user_id))
    keys = result.scalars().all()

    return [
        ApiKeyResponse(
            id=k.id,
            service=k.service,
            has_key=True,
        )
        for k in keys
    ]


@router.delete(
    "/api-keys/{service}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a saved API key",
)
async def delete_api_key(
    service: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a saved API key for a specific service."""
    service_clean = service.lower().strip()
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.service == service_clean)
    )
    key_row = result.scalar_one_or_none()
    if not key_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key for service '{service}' not found.",
        )

    await db.delete(key_row)
    await db.flush()
