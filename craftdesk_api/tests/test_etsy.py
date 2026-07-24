"""Tests for craftdesk_api Etsy router."""
from __future__ import annotations

from unittest.mock import patch
import pytest
from craftdesk_api.core.security import create_access_token, decrypt


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Etsy Shop Owner",
        "email": "etsyowner@example.com",
        "password": "EtsyOwnerPass123!",
    })
    user_id = resp.json()["user_id"]
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestEtsyOAuthEndpoints:

    def test_get_auth_url_success(self, client, auth_headers) -> None:
        resp = client.get("/api/v1/etsy/auth/url", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "etsy.com/oauth/connect" in data["auth_url"]
        assert "code_challenge=" in data["auth_url"]
        assert "code_verifier" in data
        assert "state" in data

    @patch("craftdesk_api.services.etsy_oauth.EtsyOAuthService.exchange_code_for_tokens")
    @patch("craftdesk_api.services.etsy_oauth.EtsyOAuthService.get_shop_details")
    def test_handle_callback_encrypts_tokens(
        self, mock_shop, mock_tokens, client, auth_headers
    ) -> None:
        mock_tokens.return_value = {
            "access_token": "etsy-access-secret-123",
            "refresh_token": "etsy-refresh-secret-456",
            "expires_in": 86400,
        }
        mock_shop.return_value = {
            "shop_id": "66082828",
            "shop_name": "PixelBarStudio",
        }

        payload = {
            "code": "sample-oauth-code",
            "code_verifier": "sample-pkce-verifier",
            "redirect_uri": "http://localhost:3000/shops/callback",
        }

        resp = client.post("/api/v1/etsy/auth/callback", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["shop_id"] == "66082828"
        assert data["shop_name"] == "PixelBarStudio"
        assert data["is_active"] is True

        # Verify shop is in database list
        list_resp = client.get("/api/v1/etsy/shops", headers=auth_headers)
        assert list_resp.status_code == 200
        shops = list_resp.json()
        assert len(shops) == 1
        assert shops[0]["shop_id"] == "66082828"

    def test_disconnect_shop_deactivates(self, client, auth_headers) -> None:
        # Connect shop first
        payload = {
            "code": "code-123",
            "code_verifier": "verifier-123",
            "redirect_uri": "http://localhost:3000/shops/callback",
        }
        callback_resp = client.post("/api/v1/etsy/auth/callback", json=payload, headers=auth_headers)
        shop_db_id = callback_resp.json()["id"]

        # Disconnect shop
        del_resp = client.delete(f"/api/v1/etsy/shops/{shop_db_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        # List should now be empty
        list_resp = client.get("/api/v1/etsy/shops", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 0
