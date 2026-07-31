"""Unit tests for ListingRecordWorker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from etsy_pipeline.config.settings import Settings
from etsy_pipeline.models.job import Job
from etsy_pipeline.workers.listing_record_worker import ListingRecordWorker
from etsy_pipeline.workers.etsy_worker import sort_mockup_images


def test_build_record_native_types() -> None:
    """Tags must be a list, is_digital must be bool, price must be float."""
    settings = Settings()
    worker = ListingRecordWorker(settings=settings)

    job = Job(
        job_id="test123456",
        theme="Wonder Woman",
        date_folder="2026-07-22",
        pdf_drive_link="https://drive.google.com/test",
    )
    job.etsy_title = "Wonder Woman Clipart Pack PNG"
    job.etsy_description = "High-res watercolor clipart.\nLine 2."
    job.etsy_tags = ["wonder woman clipart", "birthday png"]

    record = worker._build_record(job)

    assert record["job_id"] == "test123456"
    assert record["theme"] == "Wonder Woman"
    assert record["etsy_title"] == "Wonder Woman Clipart Pack PNG"
    # Description must be stored as-is (no \n escaping)
    assert "\n" in record["etsy_description"]
    # Tags are a native list, not pipe-delimited
    assert isinstance(record["etsy_tags"], list)
    assert record["etsy_tags"] == ["wonder woman clipart", "birthday png"]
    # is_digital is a bool, not the string "true"
    assert record["is_digital"] is True
    assert isinstance(record["listing_price_usd"], float)
    assert isinstance(record["listing_quantity"], int)
    assert isinstance(record["materials"], list)
    assert record["type"] == "download"


def test_listing_json_written_to_theme_folder(tmp_path: Path) -> None:
    """listing.json must be written inside <theme_slug>/metadata/ sub-folder."""
    settings = Settings(output_root=str(tmp_path))
    worker = ListingRecordWorker(settings=settings)

    job = Job(
        job_id="abc123",
        theme="Wonder Woman",
        date_folder="2026-07-22",
    )
    job.etsy_title = "Wonder Woman"
    job.etsy_description = "A great clipart set."
    job.etsy_tags = ["wonder woman", "clipart"]

    job = worker.run(job)

    expected = tmp_path / "2026-07-22" / job.theme_slug / "metadata" / "listing.json"
    assert expected.exists(), f"listing.json not found at {expected}"
    assert job.listing_record_path == str(expected)

    data = json.loads(expected.read_text())
    assert data["job_id"] == "abc123"
    assert isinstance(data["etsy_tags"], list)
    assert data["is_digital"] is True


def test_listing_json_stage_marked_completed(tmp_path: Path) -> None:
    """listing_record stage must be marked COMPLETED after run()."""
    settings = Settings(output_root=str(tmp_path))
    worker = ListingRecordWorker(settings=settings)

    job = Job(theme="Test Theme", date_folder="2026-07-22")
    job.etsy_title = "Title"
    job.etsy_description = "Desc"
    job.etsy_tags = ["tag1"]

    job = worker.run(job)

    from etsy_pipeline.models.job import StageStatus
    assert job.stages["listing_record"].status == StageStatus.COMPLETED


def test_sort_mockup_images_hero_first() -> None:
    """sort_mockup_images places Hero.png cover image first."""
    files = [
        Path("Main_character_1.png"),
        Path("Hero.png"),
        Path("Character_combo_2.png"),
        Path("hero.jpg"),
    ]
    sorted_files = sort_mockup_images(files)
    assert sorted_files[0].name.lower().startswith("hero")
    assert sorted_files[1].name.lower().startswith("hero")
