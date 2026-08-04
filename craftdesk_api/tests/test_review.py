"""Tests for craftdesk_api Review and Etsy Publishing router."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from craftdesk_api.core.security import create_access_token


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Reviewer User",
            "email": "reviewer@example.com",
            "password": "ReviewPass123!",
        },
    )
    user_id = resp.json()["user_id"]
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestReviewEndpoints:
    def test_get_job_review_data(self, client, auth_headers) -> None:
        # Start pipeline job first
        job_resp = client.post(
            "/api/v1/pipeline/jobs",
            json={
                "theme_name": "Review Test Theme",
            },
            headers=auth_headers,
        )
        job_id = job_resp.json()["job_id"]

        resp = client.get(f"/api/v1/review/{job_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert len(data["mockups"]) == 4
        assert "drive.google.com" in data["pdf_download_url"]
        assert data["title"].startswith("✨")

    def test_update_job_metadata(self, client, auth_headers) -> None:
        job_resp = client.post(
            "/api/v1/pipeline/jobs",
            json={
                "theme_name": "Metadata Edit Theme",
            },
            headers=auth_headers,
        )
        job_id = job_resp.json()["job_id"]

        update_payload = {
            "title": "Edited Etsy Listing Title Example",
            "description": "Edited description content with commercial license details.",
            "tags": ["tag1", "tag2", "tag3"],
        }
        resp = client.put(
            f"/api/v1/review/{job_id}/metadata",
            json=update_payload,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Edited Etsy Listing Title Example"
        assert len(data["tags"]) == 3

    @patch(
        "craftdesk_api.services.etsy_publisher.EtsyPublisherService.create_draft_listing"
    )
    def test_push_to_etsy_shop(self, mock_create, client, auth_headers) -> None:
        mock_create.return_value = {
            "listing_id": "1874290123",
            "etsy_listing_url": "https://www.etsy.com/your/shops/me/listings/1874290123",
            "status": "DRAFT",
        }

        # Start job
        job_resp = client.post(
            "/api/v1/pipeline/jobs",
            json={
                "theme_name": "Publish Theme",
            },
            headers=auth_headers,
        )
        job_id = job_resp.json()["job_id"]

        push_payload = {
            "shop_db_id": "demo-shop-id",
            "price": 5.99,
            "quantity": 999,
        }
        resp = client.post(
            f"/api/v1/review/{job_id}/push-to-etsy",
            json=push_payload,
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "DRAFT"
        assert "etsy.com" in data["etsy_listing_url"]

    def test_serve_local_media(self, client, auth_headers, tmp_path) -> None:
        # Create a mock output file inside a fake output folder
        from unittest.mock import patch

        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)
        mock_file = output_dir / "test_mockup.png"
        mock_file.write_bytes(b"dummy mockup data")

        # Mock the Path object inside the endpoint to use this temporary path
        # by temporarily resolving 'output/test_mockup.png' to our mock file path.
        with patch("craftdesk_api.routers.review.Path") as mock_path_cls:
            mock_instance = mock_path_cls.return_value
            mock_instance.exists.return_value = True
            mock_instance.is_file.return_value = True

            # 1. Successful retrieve
            with patch("fastapi.responses.FileResponse") as mock_file_response:
                mock_file_response.return_value = "dummy_response"
                resp = client.get(
                    "/api/v1/review/media?path=output/test_mockup.png",
                    headers=auth_headers,
                )
                assert resp.status_code == 200

            # 2. Directory traversal attempt
            resp = client.get(
                "/api/v1/review/media?path=output/../../etc/passwd",
                headers=auth_headers,
            )
            assert resp.status_code == 403

            # 3. Path outside output directory
            resp = client.get(
                "/api/v1/review/media?path=system/test.png",
                headers=auth_headers,
            )
            assert resp.status_code == 403
