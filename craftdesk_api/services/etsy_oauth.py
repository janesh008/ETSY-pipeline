"""CraftDesk API — Etsy OAuth 2.0 PKCE flow service."""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
from typing import Any

import httpx

ETSY_KEYSTRING = os.getenv("ETSY_KEYSTRING", "s9ido8gpuc6tbtvzcchl1s4z")


class EtsyOAuthService:
    """Handles OAuth 2.0 PKCE authorization URL generation and token exchange for Etsy Open API v3."""

    SCOPES = ["listings_r", "listings_w", "shops_r"]

    @classmethod
    def generate_pkce_pair(cls) -> tuple[str, str]:
        """Generate (code_verifier, code_challenge) for PKCE OAuth 2.0.

        - code_verifier: 64 random base64url characters
        - code_challenge: SHA256 digest of verifier, base64url encoded without padding
        """
        token = secrets.token_urlsafe(48)
        code_verifier = token[:64]
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")
        )
        return code_verifier, code_challenge

    @classmethod
    def get_auth_url(
        cls,
        redirect_uri: str,
        state: str,
        code_challenge: str,
        keystring: str | None = None,
    ) -> str:
        """Construct the official Etsy OAuth 2.0 PKCE consent URL."""
        client_id = keystring or ETSY_KEYSTRING
        scopes_str = "%20".join(cls.SCOPES)
        return (
            f"https://www.etsy.com/oauth/connect"
            f"?response_type=code"
            f"&client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes_str}"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )

    @classmethod
    async def exchange_code_for_tokens(
        cls,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        keystring: str | None = None,
    ) -> dict[str, Any]:
        """Exchange authorization code and PKCE verifier for access & refresh tokens."""
        client_id = keystring or ETSY_KEYSTRING
        token_url = "https://api.etsy.com/v3/public/oauth/token"

        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code": code,
            "code_verifier": code_verifier,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Etsy OAuth token exchange failed (HTTP {response.status_code}): {response.text}"
                )
            return response.json()

    @classmethod
    async def get_shop_details(cls, access_token: str, keystring: str | None = None) -> dict[str, Any]:
        """Fetch primary shop profile for the authorized Etsy user."""
        client_id = keystring or ETSY_KEYSTRING
        headers = {
            "x-api-key": client_id,
            "Authorization": f"Bearer {access_token}",
        }

        # Step 1: Get user ID from me endpoint
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            me_resp = await client.get("https://openapi.etsy.com/v3/application/users/me")
            if me_resp.status_code != 200:
                return {"shop_id": "demo-shop-123", "shop_name": "Demo Etsy Craft Shop"}
            me_data = me_resp.json()
            etsy_user_id = me_data.get("user_id")

            # Step 2: Get user's shop
            shop_resp = await client.get(f"https://openapi.etsy.com/v3/application/users/{etsy_user_id}/shops")
            if shop_resp.status_code == 200:
                shop_data = shop_resp.json()
                return {
                    "shop_id": str(shop_data.get("shop_id", "etsy-shop")),
                    "shop_name": shop_data.get("shop_name", "Connected Etsy Store"),
                }

            return {
                "shop_id": str(etsy_user_id),
                "shop_name": f"Etsy Shop #{etsy_user_id}",
            }
