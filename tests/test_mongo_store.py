"""Unit tests for MongoJobStore serialization and deserialization."""

from __future__ import annotations

from etsy_pipeline.models.job import Job
from etsy_pipeline.services.mongo_store import MongoJobStore


def test_job_to_dict_preserves_etsy_metadata() -> None:
    """Test _job_to_dict includes etsy_title, etsy_description, etsy_tags, and all metadata fields."""
    job = Job(
        job_id="test_meta_123",
        theme="Wonder Woman",
        date_folder="2026-07-22",
        pdf_drive_link="https://drive.google.com/test",
    )
    job.etsy_title = "Wonder Woman Clipart Pack PNG"
    job.etsy_description = "Beautiful superhero watercolor clipart bundle."
    job.etsy_tags = ["wonder woman", "clipart png", "hero graphics"]
    job.listing_price_usd = 4.99
    job.listing_quantity = 500

    data = MongoJobStore._job_to_dict(job)

    assert data["job_id"] == "test_meta_123"
    assert data["theme"] == "Wonder Woman"
    assert data["etsy_title"] == "Wonder Woman Clipart Pack PNG"
    assert data["etsy_description"] == "Beautiful superhero watercolor clipart bundle."
    assert data["etsy_tags"] == ["wonder woman", "clipart png", "hero graphics"]
    assert data["listing_price_usd"] == 4.99
    assert data["listing_quantity"] == 500
    assert data["pdf_drive_link"] == "https://drive.google.com/test"

    # Test round-trip via model_validate
    restored_job = Job.model_validate(data)
    assert restored_job.etsy_title == job.etsy_title
    assert restored_job.etsy_description == job.etsy_description
    assert restored_job.etsy_tags == job.etsy_tags
    assert restored_job.listing_price_usd == job.listing_price_usd
    assert restored_job.listing_quantity == job.listing_quantity
