"""Interactive Etsy OAuth 2.0 PKCE authentication tool.

Generates initial ETSY_ACCESS_TOKEN and ETSY_REFRESH_TOKEN for Etsy Open API v3.

Usage:
    python scripts/etsy_oauth.py
    python scripts/etsy_oauth.py --redirect-uri "http://localhost:8080/callback"
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import secrets
import sys
import urllib.parse
import webbrowser
from pathlib import Path

# Add project root to path for direct script execution
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests  # noqa: E402
from etsy_pipeline.config.settings import get_settings  # noqa: E402
from etsy_pipeline.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

DEFAULT_REDIRECT_URI = "https://localhost:8080/callback"
SCOPES = "listings_r listings_w shops_r shops_w"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Etsy OAuth 2.0 PKCE Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--redirect-uri",
        type=str,
        default=os.getenv("ETSY_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        help="Redirect URI configured in Etsy Developer App (default: https://localhost:8080/callback)",
    )
    return parser.parse_args()


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(64)[:96]
    hashed = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(hashed).decode("utf-8").replace("=", "")
    )
    return code_verifier, code_challenge


def update_env_file(access_token: str, refresh_token: str) -> None:
    """Save tokens to .env file."""
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        logger.warning(".env file not found — creating new file.")
        env_content = ""
    else:
        env_content = env_path.read_text(encoding="utf-8")

    def set_kv(content: str, key: str, val: str) -> str:
        lines = content.splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={val}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={val}")
        return "\n".join(new_lines) + "\n"

    updated = set_kv(env_content, "ETSY_ACCESS_TOKEN", access_token)
    updated = set_kv(updated, "ETSY_REFRESH_TOKEN", refresh_token)
    env_path.write_text(updated, encoding="utf-8")
    logger.info(f"Updated {env_path} with new Etsy tokens.")


def main() -> None:
    """Run interactive PKCE token exchange."""
    args = parse_args()
    settings = get_settings()
    keystring = settings.etsy_keystring
    redirect_uri = args.redirect_uri

    if not keystring:
        logger.error(
            "ETSY_KEYSTRING is missing from settings. Set ETSY_KEYSTRING in .env"
        )
        sys.exit(1)

    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    params = {
        "response_type": "code",
        "client_id": keystring,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"https://www.etsy.com/oauth/connect?{urllib.parse.urlencode(params)}"

    print("\n=======================================================")
    print("Etsy OAuth 2.0 Authentication Helper")
    print("=======================================================")
    print(f"Using Client ID (Keystring): {keystring}")
    print(f"Using Redirect URI:          {redirect_uri}")
    print("-------------------------------------------------------")
    print("Opening browser for authorization:")
    print(auth_url)
    print("=======================================================\n")
    print("NOTE: If you get 'The requested redirect URL is not permitted',")
    print("make sure the Redirect URI in your Etsy App settings matches EXACTLY.")
    print("You can pass a different URI via: --redirect-uri 'YOUR_REDIRECT_URI'\n")

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print("After authorizing, you will be redirected to your callback URL.")
    print("Copy and paste the full callback URL (or just the 'code' parameter) below:")
    callback_input = input("\nPaste callback URL or code: ").strip()

    code = callback_input
    if "code=" in callback_input:
        parsed = urllib.parse.urlparse(callback_input)
        query = urllib.parse.parse_qs(parsed.query)
        code = query.get("code", [code])[0]

    if not code:
        logger.error("No authorization code provided.")
        sys.exit(1)

    print("\nExchanging authorization code for OAuth tokens...")
    payload = {
        "grant_type": "authorization_code",
        "client_id": keystring,
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    }

    resp = requests.post(ETSY_TOKEN_URL, data=payload, timeout=30)
    if resp.status_code != 200:
        logger.error(
            f"Token exchange failed ({resp.status_code}): {resp.text}"
        )
        sys.exit(1)

    data = resp.json()
    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")

    if not access_token or not refresh_token:
        logger.error("Response did not contain valid access_token and refresh_token")
        sys.exit(1)

    print("\n✅ Successfully retrieved OAuth 2.0 Tokens!")
    print(f"Access Token:  {access_token[:15]}...")
    print(f"Refresh Token: {refresh_token[:15]}...")

    update_env_file(access_token, refresh_token)
    print("\nToken configuration saved to .env file.")


if __name__ == "__main__":
    main()
