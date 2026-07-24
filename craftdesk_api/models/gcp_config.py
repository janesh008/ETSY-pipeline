"""CraftDesk API — GcpConfig ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from craftdesk_api.db.base import Base


class GcpConfig(Base):
    """Stores GCP Compute Engine configuration for a user's GPU VM.

    Responsibility: hold the AES-256 encrypted service account JSON and
    instance details so the CraftDesk UI can start/stop the VM without
    the user opening the GCP Console.
    """

    __tablename__ = "gcp_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # GCP VM details
    project_id: Mapped[str] = mapped_column(String(255), nullable=False)
    zone: Mapped[str] = mapped_column(String(64), nullable=False)
    instance_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # AES-256 Fernet encrypted service account JSON
    encrypted_service_account_json: Mapped[str] = mapped_column(Text, nullable=False)

    # ComfyUI port on the VM (default 8188)
    comfy_ui_port: Mapped[int] = mapped_column(Integer, nullable=False, default=8188)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<GcpConfig id={self.id!r} instance={self.instance_name!r}>"
