"""Unit tests for MetadataWorker (Phase 8a of Etsy pipeline)."""

from __future__ import annotations

import pytest
from etsy_pipeline.config.settings import Settings
from etsy_pipeline.models.job import Job
from etsy_pipeline.workers.metadata_worker import MetadataWorker


@pytest.fixture
def worker() -> MetadataWorker:
    """Create a MetadataWorker instance with default settings."""
    settings = Settings()
    return MetadataWorker(settings=settings)


def test_validate_title_strips_invalid_chars(worker: MetadataWorker) -> None:
    """Test title validation strips emojis and forbidden characters."""
    raw_title = "🎨 Cute Wonder Woman Clipart Pack 🚀 ✨"
    clean = worker._validate_title(raw_title)
    assert "🚀" not in clean
    assert "✨" not in clean
    assert "Wonder Woman Clipart Pack" in clean


def test_validate_title_truncates_long_titles(worker: MetadataWorker) -> None:
    """Test title is truncated to <= 140 chars."""
    long_title = "A" * 150
    clean = worker._validate_title(long_title)
    assert len(clean) <= 140


def test_validate_title_single_restricted_chars(worker: MetadataWorker) -> None:
    """Test restricted characters (&, %, :, +) appear at most once."""
    title_with_multi_amp = "Wonder & Woman & Friends & Clipart"
    clean = worker._validate_title(title_with_multi_amp)
    assert clean.count("&") <= 1


def test_validate_tags_exact_count_and_len(worker: MetadataWorker) -> None:
    """Test tags validation outputs exactly 13 tags, each <= 20 chars."""
    raw_tags = [
        "wonder woman clipart",
        "superhero png set",
        "watercolor clipart pack",
        "nursery wall decor art",  # > 20 chars
        "sublimation design",
        "birthday invitation",
        "digital paper pack",
        "planner stickers png",
        "scrapbook element",
        "commercial use png",
    ]
    tags = worker._validate_tags(raw_tags)
    assert len(tags) == 13
    for tag in tags:
        assert len(tag) <= 20


def test_validate_description_strips_html(worker: MetadataWorker) -> None:
    """Test description validation strips HTML tags."""
    raw_desc = "<p>This is <b>bold</b> text for <a href='#'>Etsy</a></p>"
    clean = worker._validate_description(raw_desc)
    assert "<p>" not in clean
    assert "<b>" not in clean
    assert "This is bold text for Etsy" in clean
