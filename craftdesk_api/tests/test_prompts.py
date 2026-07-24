"""Tests for craftdesk_api Prompt Studio router."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from craftdesk_api.core.security import create_access_token


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Prompt User",
        "email": "prompts@example.com",
        "password": "PromptPassword123!",
    })
    user_id = resp.json()["user_id"]
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestPromptEndpoints:

    def test_generate_prompts_basic(self, client, auth_headers) -> None:
        payload = {
            "theme_text": "Wonder Woman Birthday",
            "prompt_count": 5,
        }
        resp = client.post("/api/v1/prompts/generate", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "job_id" in data
        assert data["count"] == 5
        assert len(data["prompts"]) == 5
        assert "# CraftDesk AI Prompt Set" in data["txt_content"]

    def test_export_txt_download(self, client, auth_headers) -> None:
        # Generate prompt job
        gen_resp = client.post("/api/v1/prompts/generate", json={
            "theme_text": "Cute Watercolor Animals",
            "prompt_count": 3,
        }, headers=auth_headers)
        job_id = gen_resp.json()["job_id"]

        # Export .txt
        resp = client.get(f"/api/v1/prompts/jobs/{job_id}/export", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        assert "attachment; filename=" in resp.headers["content-disposition"]
        assert "Cute Watercolor Animals" in resp.text

    @patch("craftdesk_api.services.etsy_scraper.EtsyScraperService.scrape_listing")
    def test_scrape_etsy_endpoint(self, mock_scrape, client, auth_headers) -> None:
        mock_scrape.return_value = {
            "url": "https://www.etsy.com/listing/12345/test-clipart",
            "title": "Watercolor Clipart Bundle",
            "description": "Awesome watercolor set",
            "images": ["https://img.etsy.com/1.jpg"],
        }

        resp = client.post("/api/v1/prompts/scrape-etsy", json={
            "url": "https://www.etsy.com/listing/12345/test-clipart",
        }, headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Watercolor Clipart Bundle"
        assert len(data["images"]) == 1

    def test_invalid_etsy_url_rejected(self, client, auth_headers) -> None:
        resp = client.post("/api/v1/prompts/scrape-etsy", json={
            "url": "https://google.com/invalid",
        }, headers=auth_headers)
        assert resp.status_code == 400
