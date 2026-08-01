"""Tests for craftdesk_api Etsy router."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from craftdesk_api.core.security import create_access_token


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Etsy Shop Owner",
            "email": "etsyowner@example.com",
            "password": "EtsyOwnerPass123!",
        },
    )
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

    @patch(
        "craftdesk_api.services.etsy_oauth.EtsyOAuthService.exchange_code_for_tokens"
    )
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

        resp = client.post(
            "/api/v1/etsy/auth/callback", json=payload, headers=auth_headers
        )
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

    @patch("craftdesk_api.services.etsy_oauth.EtsyOAuthService.exchange_code_for_tokens")
    @patch("craftdesk_api.services.etsy_oauth.EtsyOAuthService.get_shop_details")
    def test_disconnect_shop_deactivates(self, mock_shop, mock_tokens, client, auth_headers) -> None:
        mock_tokens.return_value = {
            "access_token": "etsy-access-secret-123",
            "refresh_token": "etsy-refresh-secret-456",
            "expires_in": 86400,
        }
        mock_shop.return_value = {
            "shop_id": "66082828",
            "shop_name": "PixelBarStudio",
        }
        # Connect shop first
        payload = {
            "code": "code-123",
            "code_verifier": "verifier-123",
            "redirect_uri": "http://localhost:3000/shops/callback",
        }
        callback_resp = client.post(
            "/api/v1/etsy/auth/callback", json=payload, headers=auth_headers
        )
        shop_db_id = callback_resp.json()["id"]

        # Disconnect shop
        del_resp = client.delete(
            f"/api/v1/etsy/shops/{shop_db_id}", headers=auth_headers
        )
        assert del_resp.status_code == 204

        # List should now be empty
        list_resp = client.get("/api/v1/etsy/shops", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 0

    def test_list_gcs_folders_endpoint(self, client, auth_headers) -> None:
        resp = client.get("/api/v1/etsy/gcs-folders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "folders" in data
        assert "gcs_available" in data

    @patch("craftdesk_api.services.etsy_oauth.EtsyOAuthService.exchange_code_for_tokens")
    @patch("craftdesk_api.services.etsy_oauth.EtsyOAuthService.get_shop_details")
    @patch("craftdesk_api.services.etsy_listing_service.EtsyListingService.publish_from_gcs")
    def test_publish_from_gcs_folder(
        self, mock_publish, mock_shop, mock_tokens, client, auth_headers
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
        # Connect shop first
        payload = {
            "code": "code-123",
            "code_verifier": "verifier-123",
            "redirect_uri": "http://localhost:3000/shops/callback",
        }
        callback_resp = client.post(
            "/api/v1/etsy/auth/callback", json=payload, headers=auth_headers
        )
        shop_db_id = callback_resp.json()["id"]

        from craftdesk_api.schemas.etsy import ListingPublishResponse

        mock_publish.return_value = ListingPublishResponse(
            listing_id="123456789",
            etsy_listing_url="https://www.etsy.com/listing/123456789",
            status="active",
            shop_name="PixelBarStudio",
            images_uploaded=4,
            pdf_uploaded=True,
            message="Published successfully.",
        )

        req_payload = {
            "gcs_prefix": "Clipart/2026-07-22/Wonder_Woman/",
            "title": "Wonder Woman Clipart Pack PNG",
            "price": 6.99,
        }
        resp = client.post(
            f"/api/v1/etsy/shops/{shop_db_id}/gcs-listing",
            json=req_payload,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["listing_id"] == "123456789"
        assert data["status"] == "active"


class TestEtsyOAuthServiceUnit:
    @pytest.mark.asyncio
    async def test_get_shop_details_raises_on_http_error(self) -> None:
        import httpx

        from craftdesk_api.services.etsy_oauth import EtsyOAuthService

        mock_resp = httpx.Response(status_code=401, text="Unauthorized")
        with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="Etsy OAuth get user details failed"):
                await EtsyOAuthService.get_shop_details("invalid_token")

    @pytest.mark.asyncio
    async def test_get_shop_details_header_contains_shared_secret(self) -> None:
        import httpx

        from craftdesk_api.services.etsy_oauth import EtsyOAuthService

        mock_resp = httpx.Response(
            status_code=200,
            json={"user_id": 12345, "shop_name": "TestShop", "shop_id": 999},
        )
        with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
            res = await EtsyOAuthService.get_shop_details(
                "token123", keystring="mykey", shared_secret="mysecret"
            )
            assert res == {"shop_id": "999", "shop_name": "TestShop"}



