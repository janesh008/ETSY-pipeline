"""CraftDesk API — application settings loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration sourced from environment / .env file.

    Responsibility: centralise every configurable value so no hardcoded
    strings exist anywhere else in craftdesk_api.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── PostgreSQL (Neon.tech) ─────────────────────────────────────────────
    database_url: str  # e.g. postgresql+asyncpg://user:pass@host/dbname

    # ── JWT ───────────────────────────────────────────────────────────────
    jwt_secret_key: str          # long random string, e.g. openssl rand -hex 32
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ── Fernet AES-256 encryption ─────────────────────────────────────────
    fernet_key: str              # base64-url-encoded 32-byte key: Fernet.generate_key()

    # ── CORS ─────────────────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:3000"]

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "CraftDesk API"
    debug: bool = False


# Single shared instance — import this everywhere
settings = Settings()
