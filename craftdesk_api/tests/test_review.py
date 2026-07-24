"""Tests for craftdesk_api Review and Etsy Publishing router."""
from __future__ import annotations

from unittest.mock import patch
import pytest
from craftdesk_api.core.security import create_access_token


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Reviewer User",
        "email": "reviewer@example.com",
        "password": "ReviewPass123!",
    })
    user_id = resp.json()["user_id"]
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestReviewEndpoints:

    def test_get_job_review_data(self, client, auth_headers) -> None:
        # Start pipeline job first
        job_resp = client.post("/api/v1/pipeline/jobs", json={
            "theme_name": "Review Test Theme",
        }, headers=auth_headers)
        job_id = job_resp.json()["job_id"]

        resp = client.get(f"/api/v1/review/{job_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert len(data["mockups"]) == 4
        assert "drive.google.com" in data["pdf_download_url"]
        assert data["title"].startswith("✨")

    def test_update_job_metadata(self, client, auth_headers) -> None:
        job_resp = client.post("/api/v1/pipeline/jobs", json={
            "theme_name": "Metadata Edit Theme",
        }, headers=auth_headers)
        job_id = job_resp.json()["job_id"]

        update_payload = {
            "title": "Edited Etsy Listing Title Example",
            "description": "Edited description content with commercial license details.",
            "tags": ["tag1", "tag2", "tag3"],
        }
        resp = client.put(f"/api/v1/review/{job_id}/metadata", json=update_payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Edited Etsy Listing Title Example"
        assert len(data["tags"]) == 3

    @patch("craftdesk_api.services.etsy_publisher.EtsyPublisherService.create_draft_listing")
    def test_push_to_etsy_shop(self, mock_create, client, auth_headers) -> None:
        mock_create.return_value = {
            "listing_id": "1874290123",
            "etsy_listing_url": "https://www.etsy.com/your/shops/me/listings/1874290123",
            "status": "DRAFT",
        }

        # Start job
        job_resp = client.post("/api/v1/pipeline/jobs", json={
            "theme_name": "Publish Theme",
        }, headers=auth_headers)
        job_id = job_resp.json()["job_id"]

        push_payload = {
            "shop_db_id": "demo-shop-id",
            "price": 5.99,
            "quantity": 999,
        }
        resp = client.post(f"/api/v1/review/{job_id}/push-to-etsy", json=push_payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "DRAFT"
        assert "etsy.com" in data["etsy_listing_url"]
