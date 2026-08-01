"""CraftDesk API — Etsy OAuth 2.0 PKCE flow service."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from typing import Any

import httpx
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


ETSY_KEYSTRING = os.getenv("ETSY_KEYSTRING", "s9ido8gpuc6tbtvzcchl1s4z")
ETSY_SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET", "")


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
    async def refresh_merchant_token(
        cls,
        refresh_token: str,
        keystring: str | None = None,
    ) -> dict[str, Any]:
        """Use refresh_token to obtain a new access_token & refresh_token from Etsy Open API v3."""
        client_id = keystring or ETSY_KEYSTRING
        token_url = "https://api.etsy.com/v3/public/oauth/token"

        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Etsy OAuth token refresh failed (HTTP {response.status_code}): {response.text}"
                )
            return response.json()

    @classmethod
    async def get_shop_details(
        cls,
        access_token: str,
        keystring: str | None = None,
        shared_secret: str | None = None,
    ) -> dict[str, Any]:
        """Fetch primary shop profile for the authorized Etsy user with debug logging at each stage."""
        from craftdesk_api.core.config import settings

        client_id = keystring or os.getenv("ETSY_KEYSTRING") or settings.etsy_keystring
        secret = shared_secret or os.getenv("ETSY_SHARED_SECRET") or settings.etsy_shared_secret

        if secret:
            api_key_header = f"{client_id}:{secret}"
            masked_key = f"{client_id[:4]}...:{secret[:2]}..."
        else:
            api_key_header = client_id
            masked_key = f"{client_id[:4]}... (NO SHARED SECRET)"

        logger.info(f"[EtsyOAuth.get_shop_details] Sourced credentials -> x-api-key: {masked_key}")

        headers = {
            "x-api-key": api_key_header,
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            # Stage 1: Request /users/me
            url_me = "https://openapi.etsy.com/v3/application/users/me"
            logger.info(f"[EtsyOAuth.get_shop_details] [Stage 1] GET {url_me}")

            try:
                me_resp = await client.get(url_me)
                logger.info(
                    f"[EtsyOAuth.get_shop_details] [Stage 1] Response status: {me_resp.status_code}"
                )

                if me_resp.status_code != 200:
                    logger.error(
                        f"[EtsyOAuth.get_shop_details] [Stage 1 ERROR] HTTP {me_resp.status_code}: {me_resp.text}"
                    )
                    raise RuntimeError(
                        f"Etsy OAuth get user details failed (HTTP {me_resp.status_code}): {me_resp.text}"
                    )

                me_data = me_resp.json()
                logger.info(
                    f"[EtsyOAuth.get_shop_details] [Stage 1 SUCCESS] me_data keys: {list(me_data.keys())}"
                )
                etsy_user_id = me_data.get("user_id")

                if "shop_name" in me_data and "shop_id" in me_data:
                    logger.info(f"[EtsyOAuth.get_shop_details] Found direct shop in /me: {me_data['shop_id']}")
                    return {
                        "shop_id": str(me_data["shop_id"]),
                        "shop_name": str(me_data["shop_name"]),
                    }

                # Stage 2: Request /users/{user_id}/shops
                if etsy_user_id:
                    url_shops = f"https://openapi.etsy.com/v3/application/users/{etsy_user_id}/shops"
                    logger.info(f"[EtsyOAuth.get_shop_details] [Stage 2] GET {url_shops}")
                    shop_resp = await client.get(url_shops)
                    logger.info(
                        f"[EtsyOAuth.get_shop_details] [Stage 2] Response status: {shop_resp.status_code}"
                    )

                    if shop_resp.status_code == 200:
                        shop_data = shop_resp.json()
                        results = shop_data.get("results", [])
                        if results and isinstance(results, list):
                            first_shop = results[0]
                            logger.info(
                                f"[EtsyOAuth.get_shop_details] [Stage 2 SUCCESS] Found shop_id: {first_shop.get('shop_id')}"
                            )
                            return {
                                "shop_id": str(first_shop.get("shop_id", etsy_user_id)),
                                "shop_name": str(first_shop.get("shop_name", f"Etsy Shop #{etsy_user_id}")),
                            }
                        elif "shop_name" in shop_data:
                            logger.info(
                                f"[EtsyOAuth.get_shop_details] [Stage 2 SUCCESS] Found shop_name in body: {shop_data.get('shop_name')}"
                            )
                            return {
                                "shop_id": str(shop_data.get("shop_id", etsy_user_id)),
                                "shop_name": str(shop_data.get("shop_name", f"Etsy Shop #{etsy_user_id}")),
                            }

                    logger.warning(
                        f"[EtsyOAuth.get_shop_details] [Stage 2 Fallback] Status {shop_resp.status_code}, returning default user shop ID."
                    )
                    return {
                        "shop_id": str(etsy_user_id),
                        "shop_name": f"Etsy User #{etsy_user_id}",
                    }

                raise RuntimeError("Etsy /users/me response missing user_id field.")

            except httpx.HTTPStatusError as http_err:
                logger.error(
                    f"[EtsyOAuth.get_shop_details] HTTPStatusError: {http_err.response.status_code} - {http_err.response.text}"
                )
                raise
            except httpx.RequestError as req_err:
                logger.error(f"[EtsyOAuth.get_shop_details] Network/RequestError: {req_err}")
                raise
            except Exception as exc:
                logger.error(f"[EtsyOAuth.get_shop_details] Unexpected Exception: {exc}", exc_info=True)
                raise


