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

    # ── PostgreSQL (Neon.tech) / SQLite fallback ─────────────────────────
    database_url: str = "sqlite+aiosqlite:///craftdesk.db"

    # ── JWT ───────────────────────────────────────────────────────────────
    jwt_secret_key: str = "craftdesk-dev-jwt-secret-key-32bytes-long!!"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ── Fernet AES-256 encryption ─────────────────────────────────────────
    fernet_key: str = "5T2W6zQ91Xk3k7p8J9mL0n2p4r6v8x1z3A5C7E9G1I3="

    # ── CORS ─────────────────────────────────────────────────────────────
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.56.1:3000",
    ]

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "CraftDesk API"
    debug: bool = True


# Single shared instance — import this everywhere
settings = Settings()
