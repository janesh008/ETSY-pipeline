"""Unit tests for EtsyWorker module."""

from __future__ import annotations

from etsy_pipeline.config.settings import Settings
from etsy_pipeline.workers.etsy_worker import EtsyWorker, sort_mockup_images
from pathlib import Path


def test_get_api_key_header_formatting() -> None:
    """Test x-api-key header combines keystring and shared_secret."""
    settings = Settings(
        etsy_keystring="test_key_123",
        etsy_shared_secret="test_secret_456",
    )
    worker = EtsyWorker(settings=settings)
    api_key = worker._get_api_key_header()
    assert api_key == "test_key_123:test_secret_456"


def test_get_api_key_header_without_secret() -> None:
    """Test x-api-key returns only keystring when shared_secret is empty."""
    settings = Settings(
        etsy_keystring="test_key_123",
        etsy_shared_secret="",
    )
    worker = EtsyWorker(settings=settings)
    api_key = worker._get_api_key_header()
    assert api_key == "test_key_123"
