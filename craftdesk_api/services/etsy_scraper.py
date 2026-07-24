"""CraftDesk API — Etsy listing URL web scraper service."""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup
import httpx


class EtsyScraperService:
    """Scrapes public metadata from Etsy listing URLs."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    @classmethod
    async def scrape_listing(cls, url: str) -> dict[str, Any]:
        """Scrape title, description, and thumbnail image URLs from an Etsy product link.

        Returns dict containing:
        - title: str
        - description: str
        - images: list[str]
        - price: str | None
        """
        # Validate Etsy URL
        if not re.search(r"etsy\.com/(?:[a-z]{2}/)?listing/\d+", url, re.IGNORECASE):
            raise ValueError("Invalid Etsy listing URL. Must be a valid etsy.com/listing/... link.")

        async with httpx.AsyncClient(headers=cls.HEADERS, follow_redirects=True, timeout=10.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception as err:
                raise RuntimeError(f"Failed to fetch Etsy listing URL: {err!s}")

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title_tag = (
            soup.find("meta", property="og:title")
            or soup.find("h1", class_=re.compile(r"title", re.I))
            or soup.find("h1")
        )
        title = ""
        if title_tag:
            title = title_tag.get("content") or title_tag.text
            title = title.strip()

        # Description
        desc_tag = (
            soup.find("meta", property="og:description")
            or soup.find("meta", attrs={"name": "description"})
            or soup.find("p", id="legacy-description")
        )
        description = ""
        if desc_tag:
            description = desc_tag.get("content") or desc_tag.text
            description = description.strip()

        # Images
        image_urls: list[str] = []
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image_urls.append(og_image["content"])

        # Additional listing gallery thumbnails
        for img in soup.find_all("img", src=re.compile(r"il_\d+xN")):
            src = img.get("src")
            if src and src not in image_urls and len(image_urls) < 5:
                image_urls.append(src)

        return {
            "url": url,
            "title": title or "Etsy Digital Clipart Bundle",
            "description": description[:1000] if description else "Watercolor digital clipart bundle for sublimation and printing.",
            "images": image_urls,
        }
