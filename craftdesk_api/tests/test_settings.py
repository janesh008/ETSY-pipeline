"""Tests for craftdesk_api Settings router."""
from __future__ import annotations

import pytest
from craftdesk_api.core.security import create_access_token


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Original Name",
        "email": "settingsuser@example.com",
        "password": "SettingsPass123!",
    })
    user_id = resp.json()["user_id"]
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestSettingsEndpoints:

    def test_update_profile_success(self, client, auth_headers) -> None:
        resp = client.put("/api/v1/settings/profile", json={
            "full_name": "Updated CraftDesk User",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Updated CraftDesk User"
        assert data["email"] == "settingsuser@example.com"

    def test_save_and_list_api_keys(self, client, auth_headers) -> None:
        # Save Gemini Key
        save_resp = client.post("/api/v1/settings/api-keys", json={
            "service": "gemini",
            "api_key": "AIzaSySecretGeminiKey123456",
        }, headers=auth_headers)
        assert save_resp.status_code == 201
        assert save_resp.json()["service"] == "gemini"

        # Save Replicate Key
        client.post("/api/v1/settings/api-keys", json={
            "service": "replicate",
            "api_key": "r8_secret_replicate_token",
        }, headers=auth_headers)

        # List keys
        list_resp = client.get("/api/v1/settings/api-keys", headers=auth_headers)
        assert list_resp.status_code == 200
        keys = list_resp.json()
        assert len(keys) == 2
        services = [k["service"] for k in keys]
        assert "gemini" in services
        assert "replicate" in services

    def test_delete_api_key(self, client, auth_headers) -> None:
        client.post("/api/v1/settings/api-keys", json={
            "service": "replicate",
            "api_key": "r8_secret_to_delete",
        }, headers=auth_headers)

        del_resp = client.delete("/api/v1/settings/api-keys/replicate", headers=auth_headers)
        assert del_resp.status_code == 204

        list_resp = client.get("/api/v1/settings/api-keys", headers=auth_headers)
        assert len(list_resp.json()) == 0
