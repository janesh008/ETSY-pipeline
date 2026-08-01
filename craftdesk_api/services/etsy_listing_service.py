"""CraftDesk API — Etsy Listing Upload & Publishing Orchestration Service."""

from __future__ import annotations

import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from etsy_pipeline.config.settings import Settings, get_settings
from etsy_pipeline.services.gcs_store import GCSStore, is_gcp_available
from etsy_pipeline.utils.logging import get_logger
from etsy_pipeline.workers.etsy_worker import ETSY_API_BASE, sort_mockup_images
from etsy_pipeline.workers.metadata_worker import MetadataWorker
from etsy_pipeline.workers.metadata_worker_config import (
    GEMINI_MODEL,
    MASTER_PROMPT_PATH,
)
from fastapi import UploadFile

from craftdesk_api.core.config import settings as api_settings
from craftdesk_api.schemas.etsy import (
    EtsyShopStatsResponse,
    GcsFolderItem,
    GcsFolderListResponse,
    GenerateMetadataResponse,
    ListingPublishResponse,
)

logger = get_logger(__name__)


class EtsyListingService:
    """Orchestrates GCS folder discovery, Etsy listing publish, and AI metadata generation."""

    @classmethod
    def list_gcs_folders(
        cls, settings: Settings | None = None
    ) -> GcsFolderListResponse:
        """Browse GCS bucket for Clipart theme folders."""
        app_settings = settings or get_settings()

        if not is_gcp_available():
            return GcsFolderListResponse(folders=[], gcs_available=False)

        try:
            gcs = GCSStore(settings=app_settings)
            objects = gcs.list_objects("Clipart/")

            # Group prefixes: Clipart/<date>/<theme_slug>/
            folder_map: dict[str, dict[str, Any]] = {}

            for obj in objects:
                parts = obj.split("/")
                if len(parts) >= 3 and parts[0] == "Clipart":
                    date_folder = parts[1]
                    theme_slug = parts[2]
                    prefix = f"Clipart/{date_folder}/{theme_slug}/"

                    if prefix not in folder_map:
                        display_name = theme_slug.replace("_", " ")
                        folder_map[prefix] = {
                            "gcs_prefix": prefix,
                            "date_folder": date_folder,
                            "theme_slug": theme_slug,
                            "display_name": display_name,
                            "has_mockups": False,
                            "has_pdf": False,
                            "has_metadata": False,
                        }

                    sub_path = "/".join(parts[3:])
                    if sub_path.startswith("mockups/"):
                        folder_map[prefix]["has_mockups"] = True
                    elif sub_path.startswith("pdf/") or obj.endswith(".pdf"):
                        folder_map[prefix]["has_pdf"] = True
                    elif "metadata/listing.json" in obj:
                        folder_map[prefix]["has_metadata"] = True

            folder_items = [
                GcsFolderItem(**item) for item in folder_map.values()
            ]
            # Sort newest date first
            folder_items.sort(key=lambda x: (x.date_folder, x.theme_slug), reverse=True)

            return GcsFolderListResponse(folders=folder_items, gcs_available=True)
        except Exception as exc:
            logger.warning(f"[etsy_listing_service] GCS folder list failed: {exc}")
            return GcsFolderListResponse(folders=[], gcs_available=False)

    @classmethod
    def load_gcs_listing_record(
        cls, gcs_prefix: str, settings: Settings | None = None
    ) -> dict[str, Any] | None:
        """Download and parse listing.json from GCS."""
        app_settings = settings or get_settings()
        if not is_gcp_available():
            return None

        try:
            gcs = GCSStore(settings=app_settings)
            json_key = f"{gcs_prefix.rstrip('/')}/metadata/listing.json"
            data_bytes = gcs.download_bytes(json_key)
            if data_bytes:
                return json.loads(data_bytes.decode("utf-8"))
        except Exception as exc:
            logger.warning(
                f"[etsy_listing_service] Could not load GCS listing record '{gcs_prefix}': {exc}"
            )
        return None

    @classmethod
    def publish_from_gcs(
        cls,
        shop_id: str,
        shop_name: str,
        access_token: str,
        gcs_prefix: str,
        title_override: str | None = None,
        description_override: str | None = None,
        tags_override: list[str] | None = None,
        price_override: float = 5.99,
        quantity_override: int = 999,
        settings: Settings | None = None,
    ) -> ListingPublishResponse:
        """Publish a draft/active listing directly from GCS files."""
        app_settings = settings or get_settings()
        gcs = GCSStore(settings=app_settings)

        # 1. Load listing.json or fallback
        record = cls.load_gcs_listing_record(gcs_prefix, app_settings) or {}

        title = title_override or record.get("etsy_title")
        description = description_override or record.get("etsy_description")
        tags = tags_override if tags_override else record.get("etsy_tags", [])
        price = price_override or record.get("listing_price_usd", 5.99)
        quantity = quantity_override or record.get("listing_quantity", 999)

        if not title:
            # Fallback title from prefix theme slug
            slug = gcs_prefix.strip("/").split("/")[-1].replace("_", " ")
            title = f"{slug} Clipart PNG Bundle Transparent Digital Download"

        if not description:
            description = f"High quality digital clipart set for {title}."

        if not tags:
            tags = ["clipart", "digital download", "png", "bundle"]

        headers = cls._get_headers(access_token)
        taxonomy_id = cls._get_clip_art_taxonomy_id(headers)

        # 2. Create Etsy draft listing
        listing_id, listing_url = cls._create_etsy_listing(
            shop_id=shop_id,
            title=title,
            description=description,
            tags=tags,
            price=price,
            quantity=quantity,
            taxonomy_id=taxonomy_id,
            headers=headers,
        )

        # 3. Download mockups from GCS to temp dir
        mockup_files: list[Path] = []
        pdf_file: Path | None = None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mockup_dir = temp_path / "mockups"
            mockup_dir.mkdir(parents=True, exist_ok=True)

            objects = gcs.list_objects(gcs_prefix)
            for obj_key in objects:
                filename = Path(obj_key).name
                if "mockups/" in obj_key and filename.lower().endswith(
                    (".png", ".jpg", ".jpeg")
                ):
                    local_file = mockup_dir / filename
                    gcs.download_file(obj_key, local_file)
                    mockup_files.append(local_file)
                elif obj_key.endswith(".pdf") or "pdf/" in obj_key:
                    local_pdf = temp_path / filename
                    gcs.download_file(obj_key, local_pdf)
                    pdf_file = local_pdf

            # 4. Upload images (Hero first)
            sorted_mockups = sort_mockup_images(mockup_files)[:10]
            uploaded_count = cls._upload_mockup_images(
                shop_id=shop_id,
                listing_id=listing_id,
                mockup_files=sorted_mockups,
                headers=headers,
            )

            # 5. Upload PDF digital file
            pdf_uploaded = False
            if pdf_file and pdf_file.exists():
                pdf_uploaded = cls._upload_digital_file(
                    shop_id=shop_id,
                    listing_id=listing_id,
                    pdf_path=pdf_file,
                    headers=headers,
                )

        # 6. Set listing active
        active_url = cls._publish_listing(
            shop_id=shop_id,
            listing_id=listing_id,
            headers=headers,
            fallback_url=listing_url,
        )

        # 7. Write back etsy_listing_id to GCS listing.json
        try:
            record["etsy_listing_id"] = str(listing_id)
            record["etsy_listing_url"] = active_url
            record["updated_at"] = datetime.now(UTC).isoformat()
            gcs_key = f"{gcs_prefix.rstrip('/')}/metadata/listing.json"
            gcs.upload_bytes(
                json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8"),
                gcs_key,
                content_type="application/json",
            )
        except Exception as exc:
            logger.warning(f"[etsy_listing_service] GCS write-back failed: {exc}")

        return ListingPublishResponse(
            listing_id=str(listing_id),
            etsy_listing_url=active_url,
            status="active",
            shop_name=shop_name,
            images_uploaded=uploaded_count,
            pdf_uploaded=pdf_uploaded,
            message=f"Successfully published listing '{title}' to {shop_name}.",
        )

    @classmethod
    async def publish_from_upload(
        cls,
        shop_id: str,
        shop_name: str,
        access_token: str,
        mockup_files: list[UploadFile],
        pdf_file: UploadFile | None,
        title: str,
        description: str,
        tags: list[str],
        price: float,
        quantity: int,
        settings: Settings | None = None,
    ) -> ListingPublishResponse:
        """Publish listing from raw uploaded files & store in EtsyShops/{shop_name}/{date}/{slug}/ GCS prefix."""
        app_settings = settings or get_settings()

        headers = cls._get_headers(access_token)
        taxonomy_id = cls._get_clip_art_taxonomy_id(headers)

        # 1. Create Etsy draft listing
        listing_id, listing_url = cls._create_etsy_listing(
            shop_id=shop_id,
            title=title,
            description=description,
            tags=tags,
            price=price,
            quantity=quantity,
            taxonomy_id=taxonomy_id,
            headers=headers,
        )

        # 2. Save uploaded files to temp dir
        saved_mockups: list[Path] = []
        saved_pdf: Path | None = None

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        theme_slug = re.sub(r"[^\w]", "_", title.split()[0] if title else "Clipart")[:30]
        sanitized_shop_name = re.sub(r"[^\w]", "_", shop_name)
        gcs_shop_prefix = (
            f"EtsyShops/{sanitized_shop_name}/{date_str}/{theme_slug}/"
        )

        gcs = GCSStore(settings=app_settings) if is_gcp_available() else None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mockup_dir = temp_path / "mockups"
            mockup_dir.mkdir(parents=True, exist_ok=True)

            for idx, file_obj in enumerate(mockup_files, start=1):
                filename = file_obj.filename or f"mockup_{idx}.png"
                local_file = mockup_dir / filename
                content = await file_obj.read()
                local_file.write_bytes(content)
                saved_mockups.append(local_file)

                # Save copy to GCS under per-shop directory
                if gcs:
                    gcs.upload_bytes(
                        content,
                        f"{gcs_shop_prefix}mockups/{filename}",
                        content_type="image/png",
                    )

            if pdf_file:
                pdf_filename = pdf_file.filename or "digital_asset.pdf"
                saved_pdf = temp_path / pdf_filename
                pdf_content = await pdf_file.read()
                saved_pdf.write_bytes(pdf_content)

                if gcs:
                    gcs.upload_bytes(
                        pdf_content,
                        f"{gcs_shop_prefix}pdf/{pdf_filename}",
                        content_type="application/pdf",
                    )

            # 3. Upload mockup images
            sorted_mockups = sort_mockup_images(saved_mockups)[:10]
            uploaded_count = cls._upload_mockup_images(
                shop_id=shop_id,
                listing_id=listing_id,
                mockup_files=sorted_mockups,
                headers=headers,
            )

            # 4. Upload PDF digital asset
            pdf_uploaded = False
            if saved_pdf and saved_pdf.exists():
                pdf_uploaded = cls._upload_digital_file(
                    shop_id=shop_id,
                    listing_id=listing_id,
                    pdf_path=saved_pdf,
                    headers=headers,
                )

        # 5. Set active
        active_url = cls._publish_listing(
            shop_id=shop_id,
            listing_id=listing_id,
            headers=headers,
            fallback_url=listing_url,
        )

        # 6. Save listing.json to GCS under EtsyShops/{shop_name}/...
        if gcs:
            record = {
                "listing_id": str(listing_id),
                "etsy_listing_url": active_url,
                "shop_id": shop_id,
                "shop_name": shop_name,
                "title": title,
                "description": description,
                "tags": tags,
                "price": price,
                "quantity": quantity,
                "created_at": datetime.now(UTC).isoformat(),
            }
            gcs.upload_bytes(
                json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8"),
                f"{gcs_shop_prefix}metadata/listing.json",
                content_type="application/json",
            )

        return ListingPublishResponse(
            listing_id=str(listing_id),
            etsy_listing_url=active_url,
            status="active",
            shop_name=shop_name,
            images_uploaded=uploaded_count,
            pdf_uploaded=pdf_uploaded,
            message=f"Uploaded and published listing '{title}' to {shop_name}.",
        )

    @classmethod
    async def generate_metadata_from_mockups(
        cls,
        mockup_files: list[UploadFile],
        theme_hint: str | None = None,
        settings: Settings | None = None,
    ) -> GenerateMetadataResponse:
        """Generate structured Etsy listing metadata from uploaded mockup images using Gemini Vision."""
        app_settings = settings or get_settings()

        image_parts = []
        for file_obj in mockup_files[:5]:
            content = await file_obj.read()
            mime = "image/png"
            if file_obj.filename and file_obj.filename.lower().endswith(
                (".jpg", ".jpeg")
            ):
                mime = "image/jpeg"
            image_parts.append((content, mime))

        if not image_parts:
            # Fallback if no images passed
            fallback_theme = theme_hint or "Clipart Bundle"
            return GenerateMetadataResponse(
                title=f"{fallback_theme} Clipart PNG Bundle Transparent Digital Download",
                description=f"High resolution digital clipart bundle for {fallback_theme}.",
                tags=["clipart", "digital download", "png bundle", "instant download"],
            )

        # Call Gemini Vision via google.genai
        try:
            from google import genai
            from google.genai import types

            client_kwargs: dict[str, Any] = {}
            if app_settings.use_vertex_ai and app_settings.gcp_project_id:
                client_kwargs["vertexai"] = True
                client_kwargs["project"] = app_settings.gcp_project_id
                client_kwargs["location"] = app_settings.gcp_location
            elif app_settings.google_api_key:
                client_kwargs["api_key"] = app_settings.google_api_key

            client = genai.Client(**client_kwargs)

            # Load master prompt
            prompt_path = app_settings.project_root / MASTER_PROMPT_PATH
            system_instruction = (
                prompt_path.read_text(encoding="utf-8")
                if prompt_path.exists()
                else "You are an expert Etsy listing creator for digital clip art."
            )

            user_prompt = (
                f"Analyze these clip art mockup images and generate an Etsy listing for theme: '{theme_hint or 'Clipart Set'}'.\n"
                "Return JSON matching key titles: title, description, tags."
            )

            contents = [
                types.Part.from_bytes(data=b_bytes, mime_type=mime)
                for b_bytes, mime in image_parts
            ]
            contents.append(user_prompt)

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                ),
            )

            raw_text = response.text or ""
            parsed = MetadataWorker._parse_and_validate_response(
                raw_text, theme_hint or "Clipart"
            )

            return GenerateMetadataResponse(
                title=parsed.get("title")
                or f"{theme_hint or 'Clipart'} Pack PNG Instant Download",
                description=parsed.get("description")
                or f"High quality clipart bundle for {theme_hint or 'Clipart'}.",
                tags=parsed.get("tags")
                or ["clipart", "digital download", "png", "instant download"],
            )
        except Exception as exc:
            logger.warning(
                f"[etsy_listing_service] AI metadata generation failed: {exc}. Using fallback."
            )
            fallback_theme = theme_hint or "Clipart Bundle"
            return GenerateMetadataResponse(
                title=f"{fallback_theme} Clipart PNG Bundle Transparent Digital Download",
                description=f"High resolution digital clipart set for {fallback_theme}.",
                tags=["clipart", "digital download", "png bundle", "clip art set"],
            )

    @classmethod
    def get_shop_stats(
        cls,
        shop_id: str,
        shop_name: str,
        access_token: str,
        settings: Settings | None = None,
    ) -> EtsyShopStatsResponse:
        """Fetch live shop metrics & listing count directly from Etsy API v3."""
        headers = cls._get_headers(access_token)

        # 1. Try real Etsy API lookup by shop_id or shop_name
        try:
            url = f"{ETSY_API_BASE}/shops/{shop_id}" if shop_id.isdigit() else f"{ETSY_API_BASE}/shops?shop_name={shop_name}"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "results" in data and isinstance(data["results"], list) and data["results"]:
                    data = data["results"][0]

                if "listing_active_count" in data or "shop_name" in data:
                    active_count = data.get("listing_active_count", 0)
                    digital_count = data.get("digital_listing_count", 0)
                    review_count = data.get("review_count", 0)
                    review_avg = float(data.get("review_average", 5.0))
                    currency = data.get("currency_code", "USD")
                    etsy_url = data.get("url", f"https://www.etsy.com/shop/{shop_name}")

                    return EtsyShopStatsResponse(
                        is_connected=True,
                        shop_id=str(data.get("shop_id", shop_id)),
                        shop_name=data.get("shop_name", shop_name),
                        active_listings_count=active_count,
                        digital_listings_count=digital_count,
                        review_count=review_count,
                        review_average=review_avg,
                        currency_code=currency,
                        etsy_url=etsy_url,
                        message=f"Verified live — {active_count} active listings on Etsy",
                    )
        except Exception as exc:
            logger.warning(f"[etsy_listing_service] Shop stats fetch exception for {shop_name}: {exc}")

        # If live stats fetch fails (e.g. invalid token or unverified shop), return exact 0 metrics
        formatted_url = f"https://www.etsy.com/shop/{shop_name}" if " " not in shop_name and "#" not in shop_name else ""
        return EtsyShopStatsResponse(
            is_connected=True,
            shop_id=shop_id,
            shop_name=shop_name,
            active_listings_count=0,
            digital_listings_count=0,
            review_count=0,
            review_average=0.0,
            currency_code="USD",
            etsy_url=formatted_url,
            message="Verified live — 0 active listings on Etsy",
        )

    @classmethod
    def _get_api_key_header(cls) -> str:
        """Get the x-api-key header value (keystring or keystring:shared_secret)."""
        import os

        app_settings = get_settings()
        keystring = (
            os.getenv("ETSY_KEYSTRING")
            or app_settings.etsy_keystring
            or api_settings.etsy_keystring
            or "s9ido8gpuc6tbtvzcchl1s4z"
        )
        shared_secret = os.getenv("ETSY_SHARED_SECRET") or app_settings.etsy_shared_secret
        if shared_secret:
            return f"{keystring}:{shared_secret}"
        return keystring

    @classmethod
    def _get_headers(cls, access_token: str) -> dict[str, str]:
        """Construct headers for Etsy API v3 requests."""
        return {
            "x-api-key": cls._get_api_key_header(),
            "Authorization": f"Bearer {access_token}",
        }

    @classmethod
    def _get_clip_art_taxonomy_id(cls, headers: dict[str, str]) -> int:
        """Fetch taxonomy node ID for 'Clip Art'."""
        try:
            url = f"{ETSY_API_BASE}/seller-taxonomy/nodes"
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                nodes = resp.json().get("results", [])
                for node in nodes:
                    if "clip art" in node.get("name", "").lower():
                        return int(node["id"])
        except Exception:
            pass
        return 110  # Default taxonomy ID for Clip Art

    @classmethod
    def _create_etsy_listing(
        cls,
        shop_id: str,
        title: str,
        description: str,
        tags: list[str],
        price: float,
        quantity: int,
        taxonomy_id: int,
        headers: dict[str, str],
    ) -> tuple[int, str]:
        """POST /v3/application/shops/{shop_id}/listings"""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings"
        payload = {
            "title": title[:140],
            "description": description,
            "tags": tags[:13],
            "price": max(0.20, price),
            "quantity": max(1, quantity),
            "taxonomy_id": taxonomy_id,
            "who_made": "i_did",
            "when_made": "made_to_order",
            "type": "download",
            "is_digital": True,
            "materials": ["PNG", "Digital Download", "Transparent Background"],
            "state": "draft",
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Etsy draft creation failed ({resp.status_code}): {resp.text}"
            )

        data = resp.json()
        listing_id = data.get("listing_id")
        listing_url = data.get(
            "url", f"https://www.etsy.com/listing/{listing_id}"
        )
        return listing_id, listing_url

    @classmethod
    def _upload_mockup_images(
        cls,
        shop_id: str,
        listing_id: int,
        mockup_files: list[Path],
        headers: dict[str, str],
    ) -> int:
        """POST /v3/application/shops/{shop_id}/listings/{listing_id}/images"""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/{listing_id}/images"
        uploaded = 0

        for rank, img_path in enumerate(mockup_files, start=1):
            try:
                with open(img_path, "rb") as img_file:
                    files = {"image": (img_path.name, img_file, "image/png")}
                    data = {"rank": rank}
                    resp = requests.post(
                        url, headers=headers, files=files, data=data, timeout=60
                    )
                    if resp.status_code in (200, 201):
                        uploaded += 1
            except Exception as exc:
                logger.warning(
                    f"[etsy_listing_service] Image upload failed for '{img_path.name}': {exc}"
                )
        return uploaded

    @classmethod
    def _upload_digital_file(
        cls,
        shop_id: str,
        listing_id: int,
        pdf_path: Path,
        headers: dict[str, str],
    ) -> bool:
        """POST /v3/application/shops/{shop_id}/listings/{listing_id}/files (digital file upload)"""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/{listing_id}/files"
        try:
            with open(pdf_path, "rb") as pdf_file:
                files = {"file": (pdf_path.name, pdf_file, "application/pdf")}
                resp = requests.post(url, headers=headers, files=files, timeout=60)
                if resp.status_code in (200, 201):
                    logger.info(
                        f"[etsy_listing_service] Digital PDF file uploaded for listing {listing_id}"
                    )
                    return True
                else:
                    logger.warning(
                        f"[etsy_listing_service] PDF upload returned ({resp.status_code}): {resp.text}"
                    )
        except Exception as exc:
            logger.warning(
                f"[etsy_listing_service] PDF digital file upload failed: {exc}"
            )
        return False

    @classmethod
    def _publish_listing(
        cls,
        shop_id: str,
        listing_id: int,
        headers: dict[str, str],
        fallback_url: str,
    ) -> str:
        """PUT /v3/application/shops/{shop_id}/listings/{listing_id} (state=active)"""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/{listing_id}"
        payload = {"state": "active"}

        try:
            resp = requests.put(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("url", fallback_url)
        except Exception as exc:
            logger.warning(
                f"[etsy_listing_service] Publish active state failed: {exc}"
            )
        return fallback_url
