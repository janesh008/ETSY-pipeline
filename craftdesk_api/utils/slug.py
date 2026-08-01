"""CraftDesk API — URL slug generation utilities."""

from __future__ import annotations

import re

from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


def slugify_shop_name(name: str) -> str:
    """Generate a clean, URL-safe slug from an Etsy shop name.

    Example:
        "PixelBarStudio" -> "pixelbarstudio"
        "Pixel Bloom Studio #12" -> "pixel-bloom-studio-12"
    """
    if not name:
        return "shop"

    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    slug = s.strip("-")

    logger.debug(f"[slugify_shop_name] Input: '{name}' -> Slug: '{slug}'")
    return slug or "shop"
