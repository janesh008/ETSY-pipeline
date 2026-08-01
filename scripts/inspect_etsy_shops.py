"""CraftDesk API — Diagnostic script to inspect users and etsy_shops tables."""

from __future__ import annotations

import asyncio
from sqlalchemy import text
from craftdesk_api.db.base import AsyncSessionLocal
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


async def inspect_db() -> None:
    async with AsyncSessionLocal() as session:
        # Check users
        users_res = await session.execute(text("SELECT id, email, full_name FROM users;"))
        users = users_res.fetchall()
        print(f"=== TOTAL USERS: {len(users)} ===")
        for u in users:
            print(f"  User -> id: '{u[0]}', email: '{u[1]}', name: '{u[2]}'")

        # Check shops
        shops_res = await session.execute(text("SELECT id, user_id, shop_id, shop_name, slug, is_active FROM etsy_shops;"))
        shops = shops_res.fetchall()
        print(f"=== TOTAL SHOPS: {len(shops)} ===")
        for s in shops:
            print(f"  Shop -> id: '{s[0]}', user_id: '{s[1]}', shop_id: '{s[2]}', name: '{s[3]}', slug: '{s[4]}', is_active: {s[5]}")



if __name__ == "__main__":
    asyncio.run(inspect_db())
