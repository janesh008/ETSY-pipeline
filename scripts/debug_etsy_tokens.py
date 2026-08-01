"""Diagnostic script to inspect Etsy OAuth tokens and print exact shop details returned by Etsy Open API v3."""

from __future__ import annotations

import os
import requests

from etsy_pipeline.config.settings import get_settings

def check_and_refresh_tokens():
    print("=" * 60)
    print("CHECKING & REFRESHING ETSY OAUTH TOKENS")
    print("=" * 60)
    
    settings = get_settings()
    keystring = settings.etsy_keystring
    shared_secret = settings.etsy_shared_secret
    access_token = settings.etsy_access_token
    refresh_token = settings.etsy_refresh_token
    configured_shop_id = settings.etsy_shop_id

    print(f"ETSY_KEYSTRING      : {keystring}")
    print(f"ETSY_SHARED_SECRET  : {'***' if shared_secret else 'NOT SET'}")
    print(f"Configured SHOP_ID  : {configured_shop_id}")
    print(f"Current ACCESS_TOKEN : {access_token[:20]}..." if access_token else "ACCESS_TOKEN: NOT SET")
    print(f"Current REFRESH_TOKEN: {refresh_token[:20]}..." if refresh_token else "REFRESH_TOKEN: NOT SET")

    api_key_header = f"{keystring}:{shared_secret}" if shared_secret else keystring
    headers = {
        "x-api-key": api_key_header,
        "Authorization": f"Bearer {access_token}",
    }

    print("\n[Step 1] Testing current Access Token via GET https://openapi.etsy.com/v3/application/users/me ...")
    resp = requests.get("https://openapi.etsy.com/v3/application/users/me", headers=headers, timeout=15)
    print(f"HTTP Status: {resp.status_code}")
    print(f"Raw Response: {resp.text}")

    if resp.status_code == 401 and refresh_token:
        print("\n[Step 2] Access Token expired. Attempting Refresh via POST https://api.etsy.com/v3/public/oauth/token ...")
        refresh_payload = {
            "grant_type": "refresh_token",
            "client_id": keystring,
            "refresh_token": refresh_token,
        }
        token_resp = requests.post("https://api.etsy.com/v3/public/oauth/token", data=refresh_payload, timeout=15)
        print(f"HTTP Status: {token_resp.status_code}")
        print(f"Raw Refresh Response: {token_resp.text}")

        if token_resp.status_code == 200:
            token_data = token_resp.json()
            access_token = token_data.get("access_token", "")
            refresh_token = token_data.get("refresh_token", "")
            print(f"\n[+] REFRESH SUCCESSFUL!")
            print(f"    New Access Token : {access_token[:20]}...")
            print(f"    New Refresh Token: {refresh_token[:20]}...")

            headers["Authorization"] = f"Bearer {access_token}"
            resp = requests.get("https://openapi.etsy.com/v3/application/users/me", headers=headers, timeout=15)
            print(f"\nRe-testing GET /users/me with NEW Access Token...")
            print(f"HTTP Status: {resp.status_code}")
            print(f"Raw Response: {resp.text}")

    if resp.status_code == 200:
        user_data = resp.json()
        user_id = user_data.get("user_id")
        print(f"\n[+] User ID from Etsy: {user_id}")

        shop_resp = requests.get(f"https://openapi.etsy.com/v3/application/users/{user_id}/shops", headers=headers, timeout=15)
        print(f"\nExecuting Etsy API Call: GET https://openapi.etsy.com/v3/application/users/{user_id}/shops ...")
        print(f"HTTP Status: {shop_resp.status_code}")
        print(f"Raw Shop Response: {shop_resp.text}")

        if shop_resp.status_code == 200:
            shop_data = shop_resp.json()
            results = shop_data.get("results", [])
            if results:
                real_shop = results[0]
                print("\n" + "=" * 60)
                print(f"[SUCCESS] REAL ETSY SHOP DETECTED FROM ETSY OPEN API v3!")
                print(f"  Exact Shop ID   : {real_shop.get('shop_id')}")
                print(f"  Exact Shop Name : {real_shop.get('shop_name')}")
                print(f"  Active Listings : {real_shop.get('listing_active_count')}")
                print(f"  Shop URL        : {real_shop.get('url')}")
                print("=" * 60)

if __name__ == "__main__":
    check_and_refresh_tokens()
