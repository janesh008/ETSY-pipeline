"""CraftDesk API — Utility script to associate existing connected Etsy shops to current user."""

from __future__ import annotations

import asyncio
from sqlalchemy import text
from craftdesk_api.db.base import AsyncSessionLocal, engine
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

TARGET_EMAIL = "janeshgem@gmail.com"


async def reassign_shops() -> None:
    async with AsyncSessionLocal() as session:
        # Find target user ID
        user_res = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": TARGET_EMAIL},
        )
        user_row = user_res.fetchone()
        if not user_row:
            print(f"Error: User {TARGET_EMAIL} not found!")
            return

        target_user_id = user_row[0]
        print(f"Target User ({TARGET_EMAIL}) ID: {target_user_id}")

        # Update all active shops to target_user_id
        update_res = await session.execute(
            text("UPDATE etsy_shops SET user_id = :user_id WHERE is_active = true"),
            {"user_id": target_user_id},
        )
        await session.commit()
        print(f"Successfully reassigned {update_res.rowcount} Etsy shops to user {TARGET_EMAIL} ({target_user_id})!")


if __name__ == "__main__":
    asyncio.run(reassign_shops())
