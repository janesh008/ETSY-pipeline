"""
Application settings — loaded from environment variables and .env file.

All hardcoded values are centralized here. Modules import `get_settings()`
to access configuration without global variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root (two levels up from this file: config/ -> etsy_pipeline/ -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Central configuration for the Etsy pipeline.

    Values are loaded from (in priority order):
    1. Environment variables
    2. .env file in the project root
    3. Default values defined here

    Usage:
        from etsy_pipeline.config.settings import get_settings
        settings = get_settings()
        print(settings.gemini_model)
    """

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- GCP / Vertex AI & Google Drive Settings ---
    gcp_project_id: str = Field(
        default="",
        description="GCP project ID for Vertex AI client",
    )
    gcp_location: str = Field(
        default="us-central1",
        description="GCP region for Vertex AI (e.g. us-central1)",
    )
    google_drive_service_account_json: str | None = Field(
        default=None,
        description="Optional local path to the Google Drive Service Account credentials JSON file",
    )
    google_drive_folder_id: str = Field(
        default="",
        description="Target Google Drive Folder ID for uploading generated assets",
    )
    gcs_bucket: str = Field(
        default="",
        description="GCS bucket name (for future Cloud Storage)",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model name for prompt/metadata generation",
    )

    # --- Paths ---
    output_root: str = Field(
        default=str(_PROJECT_ROOT / "output"),
        description="Root directory for pipeline output files",
    )
    skill_file_path: str = Field(
        default=str(
            _PROJECT_ROOT
            / "etsy_pipeline"
            / "resources"
            / "SKILL.md"
        ),
        description="Path to the SKILL.md prompt generation skill file",
    )
    metadata_skill_file_path: str = Field(
        default=str(
            _PROJECT_ROOT
            / "etsy_pipeline"
            / "resources"
            / "ETSY-Listing-Master-Prompt.txt"
        ),
        description="Path to the Etsy listing metadata generation prompt file",
    )

    # --- Logging ---
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_format: str = Field(
        default="console",
        description="Logging format: 'console' for colored output, 'json' for structured logs",
    )

    # --- Gemini API Settings ---
    gemini_temperature: float = Field(
        default=1.0,
        description="Temperature for Gemini generation (0.0 = deterministic, 2.0 = creative)",
    )
    gemini_max_output_tokens: int = Field(
        default=65536,
        description="Maximum output tokens for Gemini response",
    )

    @property
    def project_root(self) -> Path:
        """Return the resolved project root path."""
        return _PROJECT_ROOT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get the singleton Settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    Call `get_settings.cache_clear()` if you need to reload.
    """
    return Settings()
