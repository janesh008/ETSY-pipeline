"""CraftDesk API — EtsyShop ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from craftdesk_api.db.base import Base


class EtsyShop(Base):
    """Stores an Etsy shop connected via OAuth 2.0 PKCE for a CraftDesk user.

    Responsibility: hold AES-256 encrypted access/refresh tokens and shop
    metadata for multi-tenant Etsy API operations.
    """

    __tablename__ = "etsy_shops"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Etsy shop identifiers
    shop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    shop_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # AES-256 Fernet encrypted tokens
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<EtsyShop id={self.id!r} shop_name={self.shop_name!r}>"
