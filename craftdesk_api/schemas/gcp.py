"""CraftDesk API — GCP VM request/response Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GcpConfigCreate(BaseModel):
    """Payload for saving user GCP Compute Engine credentials."""

    project_id: str = Field(..., min_length=1, max_length=255)
    zone: str = Field(..., min_length=1, max_length=64, json_schema_extra={"example": "us-central1-a"})
    instance_name: str = Field(..., min_length=1, max_length=255)
    service_account_json: str = Field(
        ..., min_length=1, description="Raw GCP service account key JSON string"
    )
    comfy_ui_port: int = Field(8188, ge=1, le=65535)


class GcpConfigResponse(BaseModel):
    """Safe GCP config metadata (service account key hidden)."""

    id: str
    project_id: str
    zone: str
    instance_name: str
    comfy_ui_port: int
    has_credentials: bool = True


class VmStatusResponse(BaseModel):
    """Current GPU VM state and ComfyUI health check."""

    instance_name: str
    status: str  # "RUNNING" | "STOPPED" | "PROVISIONING" | "STAGING" | "STOPPING" | "NOT_CONFIGURED"
    external_ip: str | None = None
    comfy_ui_ready: bool = False
    comfy_ui_url: str | None = None
    message: str


class VmActionResponse(BaseModel):
    """Result of VM start/stop command."""

    instance_name: str
    action: str  # "START" | "STOP"
    status: str
    message: str
