"""CraftDesk API — ApiKey ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from craftdesk_api.db.base import Base


class ApiKey(Base):
    """Stores AES-256 encrypted external API keys (Gemini, Replicate) per user.

    Responsibility: securely persist third-party API credentials so they are
    never stored in plaintext.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Service identifier: "gemini" | "replicate"
    service: Mapped[str] = mapped_column(String(64), nullable=False)

    # AES-256 Fernet encrypted API key
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id!r} service={self.service!r}>"
