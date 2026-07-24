"""CraftDesk API — auth router: /register, /login, /refresh, /logout, /me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from craftdesk_api.db.base import get_db
from craftdesk_api.models.user import User
from craftdesk_api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserMeResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a User row by email; returns None if not found."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Fetch a User row by UUID; returns None if not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new CraftDesk account",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register a new user with email + password.

    Returns the created user profile. Raises 409 if the email is already taken.
    """
    existing = await _get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()  # populate user.id before returning

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive JWT tokens",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password; return access + refresh JWT pair.

    Returns 401 for invalid credentials (deliberately vague to prevent enumeration).
    """
    _invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = await _get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise _invalid

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new token pair",
)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validate a refresh token and issue a fresh access + refresh pair."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_error
        user_id: str = str(payload["sub"])
    except JWTError:
        raise credentials_error

    user = await _get_user_by_id(db, user_id)
    if not user:
        raise credentials_error

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (client-side token discard)",
    response_model=None,
)
async def logout() -> None:
    """Signal logout. Tokens are stateless JWTs — discard them client-side.

    Phase 2: add a server-side token denylist for hard invalidation.
    """


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current authenticated user profile",
)
async def me(
    db: AsyncSession = Depends(get_db),
    # NOTE: current_user injected via dependency in Phase 2 middleware;
    # for now accept Authorization header manually for testability
) -> UserMeResponse:
    """Placeholder — full JWT middleware dependency wired in main.py."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use /login to get tokens. /me requires auth middleware (Step 2).",
    )
