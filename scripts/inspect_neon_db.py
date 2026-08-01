"""Script to inspect Neon PostgreSQL database table etsy_shops and check stored merchant OAuth tokens."""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
from sqlalchemy import select
from craftdesk_api.db.base import AsyncSessionLocal
from craftdesk_api.models.etsy_shop import EtsyShop
from craftdesk_api.core.security import decrypt

async def inspect_db():
    print("=" * 60)
    print("INSPECTING NEON POSTGRESQL DATABASE: etsy_shops")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(EtsyShop))
        shops = result.scalars().all()

        print(f"Total Shops in Database: {len(shops)}\n")
        for i, shop in enumerate(shops, 1):
            try:
                decrypted_access = decrypt(shop.encrypted_access_token)
                decrypted_refresh = decrypt(shop.encrypted_refresh_token)
            except Exception as exc:
                decrypted_access = f"DECRYPTION ERROR: {exc}"
                decrypted_refresh = f"DECRYPTION ERROR: {exc}"

            print(f"--- Shop Record #{i} ---")
            print(f"  DB ID            : {shop.id}")
            print(f"  User ID          : {shop.user_id}")
            print(f"  Shop ID          : {shop.shop_id}")
            print(f"  Shop Name        : {shop.shop_name}")
            print(f"  Is Active        : {shop.is_active}")
            print(f"  Expires At       : {shop.token_expires_at}")
            print(f"  Created At       : {shop.created_at}")
            print(f"  Access Token     : {decrypted_access[:25]}...")
            print(f"  Refresh Token    : {decrypted_refresh[:25]}...")
            print()

if __name__ == "__main__":
    asyncio.run(inspect_db())
