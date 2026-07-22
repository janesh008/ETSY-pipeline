"""Unit tests for CSVWorker and Etsy image sorting."""

from __future__ import annotations

from pathlib import Path
from etsy_pipeline.config.settings import Settings
from etsy_pipeline.models.job import Job
from etsy_pipeline.workers.csv_worker import CSV_HEADERS, CSVWorker
from etsy_pipeline.workers.etsy_worker import sort_mockup_images


def test_csv_row_schema_headers() -> None:
    """Test CSV headers match required Etsy bulk schema."""
    assert "JOB_ID" in CSV_HEADERS
    assert "TITLE" in CSV_HEADERS
    assert "TAGS" in CSV_HEADERS
    assert "LISTING_ID" in CSV_HEADERS
    assert "LISTING_URL" in CSV_HEADERS
    assert len(CSV_HEADERS) == 18


def test_build_row_dict() -> None:
    """Test building CSV row dict from Job state."""
    settings = Settings()
    worker = CSVWorker(settings=settings)

    job = Job(
        job_id="test123456",
        theme="Wonder Woman",
        date_folder="2026-07-22",
        pdf_drive_link="https://drive.google.com/test",
    )
    job.etsy_title = "Wonder Woman Clipart Pack PNG"
    job.etsy_description = "Line 1\nLine 2"
    job.etsy_tags = ["tag1", "tag2"]

    row = worker._build_row_dict(job)
    assert row["JOB_ID"] == "test123456"
    assert row["THEME"] == "Wonder Woman"
    assert row["TITLE"] == "Wonder Woman Clipart Pack PNG"
    assert row["DESCRIPTION"] == "Line 1\\nLine 2"
    assert row["TAGS"] == "tag1|tag2"
    assert row["TYPE"] == "download"
    assert row["IS_DIGITAL"] == "true"


def test_sort_mockup_images_hero_first() -> None:
    """Test sort_mockup_images places Hero.png cover image first."""
    files = [
        Path("Main_character_1.png"),
        Path("Hero.png"),
        Path("Character_combo_2.png"),
        Path("hero.jpg"),
    ]
    sorted_files = sort_mockup_images(files)
    assert sorted_files[0].name.lower().startswith("hero")
    assert sorted_files[1].name.lower().startswith("hero")
