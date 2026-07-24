"""CraftDesk API — GCP Compute Engine router: config, VM start/stop, health check."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.core.security import decrypt, decode_token, encrypt
from craftdesk_api.db.base import get_db
from craftdesk_api.models.gcp_config import GcpConfig
from craftdesk_api.schemas.gcp import (
    GcpConfigCreate,
    GcpConfigResponse,
    VmActionResponse,
    VmStatusResponse,
)
from craftdesk_api.services.gcp_vm import GcpVmService

router = APIRouter(prefix="/gcp", tags=["gcp"])


# ── Auth Helper ───────────────────────────────────────────────────────────────

async def get_current_user_id(authorization: str | None = Header(None)) -> str:
    """Extract and verify user UUID from 'Authorization: Bearer <token>' header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ")[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type.",
            )
        return str(payload["sub"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _get_user_gcp_config(db: AsyncSession, user_id: str) -> GcpConfig | None:
    """Fetch GcpConfig row for user_id."""
    result = await db.execute(select(GcpConfig).where(GcpConfig.user_id == user_id))
    return result.scalar_one_or_none()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/config",
    response_model=GcpConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save or update GCP service account and VM configuration",
)
async def save_gcp_config(
    body: GcpConfigCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> GcpConfigResponse:
    """Save encrypted GCP service account JSON and VM details for the authenticated user."""
    existing = await _get_user_gcp_config(db, user_id)

    encrypted_json = encrypt(body.service_account_json)

    if existing:
        existing.project_id = body.project_id
        existing.zone = body.zone
        existing.instance_name = body.instance_name
        existing.encrypted_service_account_json = encrypted_json
        existing.comfy_ui_port = body.comfy_ui_port
        gcp_cfg = existing
    else:
        gcp_cfg = GcpConfig(
            user_id=user_id,
            project_id=body.project_id,
            zone=body.zone,
            instance_name=body.instance_name,
            encrypted_service_account_json=encrypted_json,
            comfy_ui_port=body.comfy_ui_port,
        )
        db.add(gcp_cfg)

    await db.flush()

    return GcpConfigResponse(
        id=gcp_cfg.id,
        project_id=gcp_cfg.project_id,
        zone=gcp_cfg.zone,
        instance_name=gcp_cfg.instance_name,
        comfy_ui_port=gcp_cfg.comfy_ui_port,
        has_credentials=True,
    )


@router.get(
    "/config",
    response_model=GcpConfigResponse,
    summary="Get user GCP VM config metadata",
)
async def get_gcp_config(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> GcpConfigResponse:
    """Fetch saved GCP VM config metadata (hides service account key)."""
    gcp_cfg = await _get_user_gcp_config(db, user_id)
    if not gcp_cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GCP configuration not found for this user.",
        )

    return GcpConfigResponse(
        id=gcp_cfg.id,
        project_id=gcp_cfg.project_id,
        zone=gcp_cfg.zone,
        instance_name=gcp_cfg.instance_name,
        comfy_ui_port=gcp_cfg.comfy_ui_port,
        has_credentials=True,
    )


@router.post(
    "/vm/start",
    response_model=VmActionResponse,
    summary="Start the GCP Compute Engine GPU VM",
)
async def start_vm(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> VmActionResponse:
    """Trigger `instances().start()` on the user's configured GCP Compute Engine GPU VM."""
    gcp_cfg = await _get_user_gcp_config(db, user_id)
    if not gcp_cfg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please save your GCP configuration in Settings first.",
        )

    service_account_json = decrypt(gcp_cfg.encrypted_service_account_json)

    try:
        GcpVmService.start_vm(
            project_id=gcp_cfg.project_id,
            zone=gcp_cfg.zone,
            instance_name=gcp_cfg.instance_name,
            service_account_json_str=service_account_json,
        )
        return VmActionResponse(
            instance_name=gcp_cfg.instance_name,
            action="START",
            status="STARTING",
            message="GPU VM start signal sent. Booting instance and ComfyUI server...",
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GCP API Error: {err!s}",
        )


@router.post(
    "/vm/stop",
    response_model=VmActionResponse,
    summary="Stop the GCP Compute Engine GPU VM to save costs",
)
async def stop_vm(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> VmActionResponse:
    """Trigger `instances().stop()` on the user's GPU VM to save GCP compute costs."""
    gcp_cfg = await _get_user_gcp_config(db, user_id)
    if not gcp_cfg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please save your GCP configuration in Settings first.",
        )

    service_account_json = decrypt(gcp_cfg.encrypted_service_account_json)

    try:
        GcpVmService.stop_vm(
            project_id=gcp_cfg.project_id,
            zone=gcp_cfg.zone,
            instance_name=gcp_cfg.instance_name,
            service_account_json_str=service_account_json,
        )
        return VmActionResponse(
            instance_name=gcp_cfg.instance_name,
            action="STOP",
            status="STOPPING",
            message="GPU VM stop signal sent to save GCP costs.",
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GCP API Error: {err!s}",
        )


@router.get(
    "/vm/status",
    response_model=VmStatusResponse,
    summary="Get VM status and ComfyUI health readiness",
)
async def get_vm_status(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> VmStatusResponse:
    """Fetch current status of the VM from GCP API, and verify if ComfyUI is responding on port 8188."""
    gcp_cfg = await _get_user_gcp_config(db, user_id)
    if not gcp_cfg:
        return VmStatusResponse(
            instance_name="Unconfigured",
            status="NOT_CONFIGURED",
            external_ip=None,
            comfy_ui_ready=False,
            comfy_ui_url=None,
            message="No GCP configuration saved.",
        )

    service_account_json = decrypt(gcp_cfg.encrypted_service_account_json)

    try:
        vm_details = GcpVmService.get_vm_details(
            project_id=gcp_cfg.project_id,
            zone=gcp_cfg.zone,
            instance_name=gcp_cfg.instance_name,
            service_account_json_str=service_account_json,
        )

        status_str = vm_details["status"]
        ip = vm_details["external_ip"]
        comfy_ready = False
        comfy_url = None

        if status_str == "RUNNING" and ip:
            comfy_ready = await GcpVmService.check_comfy_ui_health(
                host=ip, port=gcp_cfg.comfy_ui_port
            )
            comfy_url = f"http://{ip}:{gcp_cfg.comfy_ui_port}"

        message_text = f"VM status is {status_str}."
        if comfy_ready:
            message_text = f"GPU VM Ready ✅. ComfyUI responding at {comfy_url}"
        elif status_str == "RUNNING":
            message_text = f"VM is RUNNING, but ComfyUI at {comfy_url} is still starting up..."

        return VmStatusResponse(
            instance_name=gcp_cfg.instance_name,
            status=status_str,
            external_ip=ip,
            comfy_ui_ready=comfy_ready,
            comfy_ui_url=comfy_url,
            message=message_text,
        )

    except Exception as err:
        return VmStatusResponse(
            instance_name=gcp_cfg.instance_name,
            status="UNKNOWN",
            external_ip=None,
            comfy_ui_ready=False,
            comfy_ui_url=None,
            message=f"Error checking VM status: {err!s}",
        )
