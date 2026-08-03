"""CraftDesk API — Etsy Shop Connector router: OAuth 2.0 PKCE, token encryption, and shop CRUD."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from etsy_pipeline.config.settings import get_settings
from etsy_pipeline.services.gcs_store import GCSStore, is_gcp_available
from etsy_pipeline.utils.logging import get_logger
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.core.security import decrypt, encrypt
from craftdesk_api.db.base import get_db
from craftdesk_api.models.etsy_shop import EtsyShop
from craftdesk_api.routers.gcp import get_current_user_id
from craftdesk_api.schemas.etsy import (
    EtsyAuthUrlResponse,
    EtsyCallbackRequest,
    EtsyShopCreateRequest,
    EtsyShopResponse,
    EtsyShopStatsResponse,
    EtsyShopUpdateRequest,
    GcsFolderDetailsResponse,
    GcsFolderListResponse,
    GcsListingRequest,
    GenerateMetadataResponse,
    ListingPublishResponse,
)
from craftdesk_api.services.etsy_listing_service import EtsyListingService
from craftdesk_api.services.etsy_oauth import EtsyOAuthService
from craftdesk_api.utils.slug import slugify_shop_name

logger = get_logger(__name__)

router = APIRouter(prefix="/etsy", tags=["etsy"])


@router.get(
    "/auth/url",
    response_model=EtsyAuthUrlResponse,
    summary="Generate Etsy OAuth 2.0 PKCE authorization consent URL",
)
async def get_etsy_auth_url(
    redirect_uri: str = "http://localhost:3000/shops/callback",
    user_id: str = Depends(get_current_user_id),
) -> EtsyAuthUrlResponse:
    """Generate PKCE verifier, challenge, and official Etsy OAuth consent URL."""
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = EtsyOAuthService.generate_pkce_pair()
    auth_url = EtsyOAuthService.get_auth_url(
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=code_challenge,
    )

    return EtsyAuthUrlResponse(
        auth_url=auth_url,
        state=state,
        code_verifier=code_verifier,
    )


@router.post(
    "/auth/callback",
    response_model=EtsyShopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Exchange OAuth code for tokens, encrypt with AES-256, and connect shop",
)
async def handle_etsy_callback(
    body: EtsyCallbackRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> EtsyShopResponse:
    """Exchange authorization code and PKCE verifier for tokens, encrypt tokens with Fernet AES-256, and save shop."""
    try:
        token_data = await EtsyOAuthService.exchange_code_for_tokens(
            code=body.code,
            code_verifier=body.code_verifier,
            redirect_uri=body.redirect_uri,
        )
    except Exception as exc:
        logger.error(f"[etsy_oauth_callback] OAuth token exchange failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Etsy OAuth code exchange failed: {exc}",
        ) from exc

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data.get("expires_in", 86400)

    # Fetch real shop profile from Etsy API
    try:
        shop_info = await EtsyOAuthService.get_shop_details(access_token)
        shop_id = shop_info["shop_id"]
        shop_name = shop_info["shop_name"]
    except Exception as exc:
        logger.error(f"[etsy_oauth_callback] Failed to fetch shop details from Etsy: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch connected Etsy shop profile: {exc}",
        ) from exc

    # Encrypt tokens with AES-256 Fernet
    encrypted_access = encrypt(access_token)
    encrypted_refresh = encrypt(refresh_token)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    shop_slug = slugify_shop_name(shop_name)

    # Check if shop already connected for this user
    result = await db.execute(
        select(EtsyShop).where(EtsyShop.user_id == user_id, EtsyShop.shop_id == shop_id)
    )
    existing_shop = result.scalar_one_or_none()

    if existing_shop:
        existing_shop.shop_name = shop_name
        existing_shop.slug = shop_slug
        existing_shop.encrypted_access_token = encrypted_access
        existing_shop.encrypted_refresh_token = encrypted_refresh
        existing_shop.token_expires_at = expires_at
        existing_shop.is_active = True
        shop_row = existing_shop
    else:
        shop_row = EtsyShop(
            user_id=user_id,
            shop_id=shop_id,
            shop_name=shop_name,
            slug=shop_slug,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expires_at=expires_at,
            is_active=True,
        )
        db.add(shop_row)

    await db.flush()

    return EtsyShopResponse(
        id=shop_row.id,
        shop_id=shop_row.shop_id,
        shop_name=shop_row.shop_name,
        slug=shop_row.slug or shop_slug,
        is_active=shop_row.is_active,
        created_at=shop_row.created_at,
    )



@router.post(
    "/shops",
    response_model=EtsyShopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new Etsy shop with custom name",
)
async def create_custom_shop(
    body: EtsyShopCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> EtsyShopResponse:
    """Manually add/register a new Etsy shop connection."""
    shop_id = body.shop_id or f"shop-{secrets.token_hex(4)}"
    demo_token = f"custom-access-token-{secrets.token_hex(16)}"
    encrypted_access = encrypt(demo_token)
    encrypted_refresh = encrypt(demo_token)

    shop_slug = slugify_shop_name(body.shop_name)
    shop_row = EtsyShop(
        user_id=user_id,
        shop_id=shop_id,
        shop_name=body.shop_name,
        slug=shop_slug,
        encrypted_access_token=encrypted_access,
        encrypted_refresh_token=encrypted_refresh,
        token_expires_at=datetime.now(UTC) + timedelta(days=30),
        is_active=True,
    )
    db.add(shop_row)
    await db.flush()

    return EtsyShopResponse(
        id=shop_row.id,
        shop_id=shop_row.shop_id,
        shop_name=shop_row.shop_name,
        slug=shop_row.slug or shop_slug,
        is_active=shop_row.is_active,
        created_at=shop_row.created_at,
    )


@router.get(
    "/shops",
    response_model=list[EtsyShopResponse],
    summary="List all connected Etsy shops for the authenticated user",
)
async def list_user_shops(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[EtsyShopResponse]:
    """Fetch all active connected Etsy shops for current user."""
    result = await db.execute(
        select(EtsyShop).where(EtsyShop.user_id == user_id, EtsyShop.is_active.is_(True))
    )
    shops = result.scalars().all()

    return [
        EtsyShopResponse(
            id=s.id,
            shop_id=s.shop_id,
            shop_name=s.shop_name,
            slug=s.slug or slugify_shop_name(s.shop_name),
            is_active=s.is_active,
            created_at=s.created_at,
        )
        for s in shops
    ]



async def get_valid_merchant_access_token(shop_row: EtsyShop, db: AsyncSession) -> str:
    """Ensure merchant access token from Neon DB is valid and fresh. Refresh from Etsy if expired."""
    access_token = decrypt(shop_row.encrypted_access_token)
    refresh_token = decrypt(shop_row.encrypted_refresh_token)

    now = datetime.now(UTC)
    token_exp = shop_row.token_expires_at
    if token_exp and token_exp.tzinfo is None:
        token_exp = token_exp.replace(tzinfo=UTC)

    is_expired = token_exp is not None and now >= (token_exp - timedelta(minutes=5))

    if is_expired and refresh_token and not refresh_token.startswith("demo-"):
        logger.info(
            f"[etsy_token_lifecycle] Access token for shop {shop_row.shop_name} ({shop_row.shop_id}) expired. Refreshing via Etsy OAuth API..."
        )
        try:
            new_tokens = await EtsyOAuthService.refresh_merchant_token(refresh_token)
            new_access = new_tokens.get("access_token")
            new_refresh = new_tokens.get("refresh_token", refresh_token)
            expires_in = new_tokens.get("expires_in", 3600)

            if new_access:
                access_token = new_access
                shop_row.encrypted_access_token = encrypt(new_access)
                shop_row.encrypted_refresh_token = encrypt(new_refresh)
                shop_row.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
                await db.flush()
                logger.info(
                    f"[etsy_token_lifecycle] Merchant tokens successfully refreshed and saved to Neon DB for shop {shop_row.shop_name}!"
                )
        except Exception as exc:
            logger.warning(
                f"[etsy_token_lifecycle] Merchant token refresh failed for shop {shop_row.shop_id}: {exc}"
            )

    print("=" * 70)
    print(" [DIAGNOSTIC LOG] Merchant API Request Execution")
    print(f"  Merchant User ID    : {shop_row.user_id}")
    print(f"  Database Shop DB ID : {shop_row.id}")
    print(f"  Database Shop ID    : {shop_row.shop_id}")
    print(f"  Shop Display Name   : {shop_row.shop_name}")
    print("  Token Storage Source: Neon PostgreSQL (etsy_shops table)")
    print(f"  Access Token Prefix : {access_token[:16]}...")
    print(f"  Token Expiration    : {shop_row.token_expires_at}")
    print("=" * 70)

    return access_token


async def get_shop_by_identifier(
    identifier: str, user_id: str, db: AsyncSession
) -> EtsyShop:
    """Resolve an EtsyShop by URL slug, shop_name, shop_id, or database id (UUID)."""
    clean_id = identifier.strip()
    stmt = select(EtsyShop).where(
        EtsyShop.user_id == user_id,
        EtsyShop.is_active.is_(True),
        or_(
            EtsyShop.slug == clean_id.lower(),
            EtsyShop.shop_name == clean_id,
            EtsyShop.shop_id == clean_id,
            EtsyShop.id == clean_id,
        ),
    )
    result = await db.execute(stmt)
    shop_row = result.scalar_one_or_none()
    if not shop_row:
        logger.error(
            f"[get_shop_by_identifier] Active Etsy shop not found for identifier='{identifier}', user_id='{user_id}'"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active connected Etsy shop '{identifier}' not found.",
        )
    return shop_row


@router.get(
    "/shops/{shop_identifier}/stats",
    response_model=EtsyShopStatsResponse,
    summary="Verify shop connection & fetch live active listings and reviews counts from Etsy API v3",
)
async def get_shop_stats(
    shop_identifier: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> EtsyShopStatsResponse:
    """Fetch live listing count and shop connection details directly from Etsy Open API v3."""
    shop_row = await get_shop_by_identifier(shop_identifier, user_id, db)
    access_token = await get_valid_merchant_access_token(shop_row, db)
    return EtsyListingService.get_shop_stats(
        shop_id=shop_row.shop_id,
        shop_name=shop_row.shop_name,
        access_token=access_token,
    )


@router.patch(
    "/shops/{shop_identifier}",
    response_model=EtsyShopResponse,
    summary="Update connected Etsy shop details (e.g. shop name)",
)
async def update_shop_details(
    shop_identifier: str,
    body: EtsyShopUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> EtsyShopResponse:
    """Edit the display name of a connected Etsy shop."""
    shop_row = await get_shop_by_identifier(shop_identifier, user_id, db)
    shop_row.shop_name = body.shop_name
    shop_row.slug = slugify_shop_name(body.shop_name)
    await db.flush()

    return EtsyShopResponse(
        id=shop_row.id,
        shop_id=shop_row.shop_id,
        shop_name=shop_row.shop_name,
        slug=shop_row.slug,
        is_active=shop_row.is_active,
        created_at=shop_row.created_at,
    )


@router.delete(
    "/shops/{shop_identifier}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Disconnect an Etsy shop",
)
async def disconnect_shop(
    shop_identifier: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete / deactivate a connected Etsy shop connection."""
    shop_row = await get_shop_by_identifier(shop_identifier, user_id, db)
    shop_row.is_active = False
    await db.flush()



# ── Listing Upload & Publish Endpoints ────────────────────────────────────


@router.get(
    "/gcs-folders",
    response_model=GcsFolderListResponse,
    summary="List available GCS clipart theme folders for publishing",
)
async def list_gcs_folders(
    user_id: str = Depends(get_current_user_id),
) -> GcsFolderListResponse:
    """Browse GCS bucket for available Clipart theme folders."""
    return EtsyListingService.list_gcs_folders()


@router.get(
    "/gcs-folder-details",
    response_model=GcsFolderDetailsResponse,
    summary="Get metadata and mockup images for a specific GCS clipart theme folder",
)
async def get_gcs_folder_details(
    gcs_prefix: str,
    user_id: str = Depends(get_current_user_id),
) -> GcsFolderDetailsResponse:
    """Fetch listing.json metadata and mockup image object keys for a given GCS folder prefix."""
    return EtsyListingService.get_gcs_folder_details(gcs_prefix)


# Server-side in-memory cache for media bytes (object_key -> (bytes, media_type))
_MEDIA_BYTES_CACHE: dict[str, tuple[bytes, str]] = {}


@router.get(
    "/gcs-media",
    summary="Proxy stream or fetch GCS image binary for browser display",
)
async def get_gcs_media(
    object_key: str,
) -> Response:
    """Stream raw image bytes from GCS bucket for browser thumbnail/lightbox rendering."""
    headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "ETag": f'"{abs(hash(object_key))}"',
    }

    if object_key in _MEDIA_BYTES_CACHE:
        data, media_type = _MEDIA_BYTES_CACHE[object_key]
        return Response(content=data, media_type=media_type, headers=headers)

    if not is_gcp_available():
        raise HTTPException(status_code=404, detail="GCP credentials not available")

    try:
        app_settings = get_settings()
        gcs = GCSStore(settings=app_settings)
        data = gcs.download_bytes(object_key)
        media_type = "image/png" if object_key.lower().endswith(".png") else "image/jpeg"

        # Cache in memory (cap at 300 images)
        if len(_MEDIA_BYTES_CACHE) > 300:
            _MEDIA_BYTES_CACHE.clear()
        _MEDIA_BYTES_CACHE[object_key] = (data, media_type)

        return Response(
            content=data,
            media_type=media_type,
            headers=headers,
        )
    except Exception as exc:
        logger.warning(f"[etsy_router] GCS media proxy failed for '{object_key}': {exc}")
        raise HTTPException(status_code=404, detail=f"Image object '{object_key}' not found")





@router.post(
    "/shops/{shop_identifier}/gcs-listing",
    response_model=ListingPublishResponse,
    summary="Publish an Etsy listing directly from a GCS folder",
)
async def publish_from_gcs_folder(
    shop_identifier: str,
    body: GcsListingRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ListingPublishResponse:
    """Fetch decrypted shop tokens and publish GCS clipart folder directly to Etsy."""
    shop_row = await get_shop_by_identifier(shop_identifier, user_id, db)
    access_token = await get_valid_merchant_access_token(shop_row, db)

    try:
        return EtsyListingService.publish_from_gcs(
            shop_id=shop_row.shop_id,
            shop_name=shop_row.shop_name,
            access_token=access_token,
            gcs_prefix=body.gcs_prefix,
            title_override=body.title,
            description_override=body.description,
            tags_override=body.tags,
            price_override=body.price,
            quantity_override=body.quantity,
            is_ai_created_override=body.is_ai_created,
            renewal_option_override=body.renewal_option,
        )
    except Exception as exc:
        logger.error(
            f"[publish_from_gcs_folder] Failed to publish GCS listing for shop '{shop_identifier}': {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to publish listing from GCS: {exc}",
        ) from exc


@router.post(
    "/shops/{shop_identifier}/upload-listing",
    response_model=ListingPublishResponse,
    summary="Upload custom mockup images & PDF asset and publish directly to Etsy",
)
async def publish_from_manual_upload(
    shop_identifier: str,
    mockup_files: list[UploadFile] = File(...),
    pdf_file: UploadFile | None = File(default=None),
    title: str = Form(...),
    description: str = Form(...),
    tags: str = Form(default=""),
    price: float = Form(default=5.99),
    quantity: int = Form(default=999),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ListingPublishResponse:
    """Accept uploaded mockup images & PDF asset and publish to Etsy."""
    shop_row = await get_shop_by_identifier(shop_identifier, user_id, db)
    access_token = await get_valid_merchant_access_token(shop_row, db)
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()][:13]

    try:
        return await EtsyListingService.publish_from_upload(
            shop_id=shop_row.shop_id,
            shop_name=shop_row.shop_name,
            access_token=access_token,
            mockup_files=mockup_files,
            pdf_file=pdf_file,
            title=title,
            description=description,
            tags=parsed_tags,
            price=price,
            quantity=quantity,
        )
    except Exception as exc:
        logger.error(
            f"[publish_from_manual_upload] Failed to publish manual upload for shop '{shop_identifier}': {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to publish uploaded listing: {exc}",
        ) from exc


@router.post(
    "/shops/{shop_identifier}/generate-metadata",
    response_model=GenerateMetadataResponse,
    summary="Generate Etsy title, description, and tags from uploaded mockup images via Gemini Vision",
)
async def generate_metadata_from_upload(
    shop_identifier: str,
    mockup_files: list[UploadFile] = File(...),
    theme_hint: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
) -> GenerateMetadataResponse:
    """Generate title, description, and 13 tags from uploaded mockup images using Gemini 2.5 Flash."""
    try:
        return await EtsyListingService.generate_metadata_from_mockups(
            mockup_files=mockup_files,
            theme_hint=theme_hint,
        )
    except Exception as exc:
        logger.error(f"[generate_metadata_from_upload] Metadata generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metadata generation failed: {exc}",
        ) from exc


