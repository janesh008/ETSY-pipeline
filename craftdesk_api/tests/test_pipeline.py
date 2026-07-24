"""Tests for craftdesk_api 6-stage Pipeline execution router."""
from __future__ import annotations

import pytest
from craftdesk_api.core.security import create_access_token


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Pipeline User",
        "email": "pipeline@example.com",
        "password": "PipelinePass123!",
    })
    user_id = resp.json()["user_id"]
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestPipelineEndpoints:

    def test_start_pipeline_job(self, client, auth_headers) -> None:
        payload = {
            "theme_name": "Wonder Woman Birthday",
            "prompts": ["Digital watercolor clipart of Wonder Woman"],
        }
        resp = client.post("/api/v1/pipeline/jobs", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "job_id" in data
        assert len(data["stages"]) == 6
        assert data["stages"][0]["stage_name"] == "image_gen"

    def test_get_job_and_stages(self, client, auth_headers) -> None:
        # Start job
        start_resp = client.post("/api/v1/pipeline/jobs", json={
            "theme_name": "Watercolor Clipart Set",
        }, headers=auth_headers)
        job_id = start_resp.json()["job_id"]

        # Get job
        job_resp = client.get(f"/api/v1/pipeline/jobs/{job_id}", headers=auth_headers)
        assert job_resp.status_code == 200
        assert job_resp.json()["job_id"] == job_id

        # Get stages
        stages_resp = client.get(f"/api/v1/pipeline/jobs/{job_id}/stages", headers=auth_headers)
        assert stages_resp.status_code == 200
        assert len(stages_resp.json()) == 6

    def test_retry_failed_stage(self, client, auth_headers) -> None:
        start_resp = client.post("/api/v1/pipeline/jobs", json={
            "theme_name": "Retry Test Theme",
        }, headers=auth_headers)
        job_id = start_resp.json()["job_id"]

        # Retry stage
        retry_resp = client.post(
            f"/api/v1/pipeline/jobs/{job_id}/stages/image_gen/retry",
            headers=auth_headers,
        )
        assert retry_resp.status_code == 200
        data = retry_resp.json()
        image_gen_stage = next(s for s in data["stages"] if s["stage_name"] == "image_gen")
        assert image_gen_stage["status"] in ("pending", "running")
        assert image_gen_stage["error_message"] is None
