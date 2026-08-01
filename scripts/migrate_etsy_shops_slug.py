"""CraftDesk API — Migration script to add 'slug' column to 'etsy_shops' table."""

from __future__ import annotations

import asyncio
from sqlalchemy import text
from craftdesk_api.db.base import engine, AsyncSessionLocal
from craftdesk_api.utils.slug import slugify_shop_name
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


async def migrate_slug_column() -> None:
    logger.info("[migrate_slug_column] Starting database migration for etsy_shops.slug...")

    async with engine.begin() as conn:
        # Add column if not exists
        await conn.execute(
            text("ALTER TABLE etsy_shops ADD COLUMN IF NOT EXISTS slug VARCHAR(255) DEFAULT '' NOT NULL;")
        )
        logger.info("[migrate_slug_column] Column 'slug' ensured on table 'etsy_shops'.")

    # Populate existing rows with clean slugs
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id, shop_name, slug FROM etsy_shops;"))
        rows = result.fetchall()
        for row in rows:
            shop_id, shop_name, current_slug = row
            if not current_slug:
                new_slug = slugify_shop_name(shop_name or "shop")
                await session.execute(
                    text("UPDATE etsy_shops SET slug = :slug WHERE id = :id"),
                    {"slug": new_slug, "id": shop_id},
                )
                logger.info(f"[migrate_slug_column] Updated shop id='{shop_id}', name='{shop_name}' -> slug='{new_slug}'")
        await session.commit()

    logger.info("[migrate_slug_column] Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate_slug_column())
