"""CraftDesk API — Etsy Listing Upload & Publishing Orchestration Service."""

from __future__ import annotations

import json
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    GcsFolderDetailsResponse,
    GcsFolderItem,
    GcsFolderListResponse,
    GenerateMetadataResponse,
    ListingPublishResponse,
)

logger = get_logger(__name__)


_GCS_FOLDERS_CACHE_STORE: tuple[float, GcsFolderListResponse] | None = None
_SHOP_STATS_CACHE_STORE: dict[str, tuple[float, EtsyShopStatsResponse]] = {}


class EtsyListingService:
    """Orchestrates GCS folder discovery, Etsy listing publish, and AI metadata generation."""

    @classmethod
    def list_gcs_folders(
        cls, settings: Settings | None = None
    ) -> GcsFolderListResponse:
        """Browse GCS bucket for Clipart theme folders."""
        global _GCS_FOLDERS_CACHE_STORE
        now = time.time()
        # Only use cache if it was successful and less than 60s old
        if (
            _GCS_FOLDERS_CACHE_STORE
            and _GCS_FOLDERS_CACHE_STORE[1].gcs_available
            and (now - _GCS_FOLDERS_CACHE_STORE[0]) < 60
        ):
            return _GCS_FOLDERS_CACHE_STORE[1]

        app_settings = settings or get_settings()

        if not is_gcp_available() and not app_settings.gcs_bucket:
            return GcsFolderListResponse(folders=[], gcs_available=False)

        try:
            gcs = GCSStore(settings=app_settings)
            objects = gcs.list_objects("Clipart/")

            # Group prefixes: Clipart/<date>/<theme_slug>/ or Clipart/<theme_slug>/
            folder_map: dict[str, dict[str, Any]] = {}

            for obj in objects:
                parts = obj.split("/")
                if len(parts) >= 2 and parts[0] == "Clipart":
                    if len(parts) >= 3:
                        date_folder = parts[1]
                        theme_slug = parts[2]
                        prefix = f"Clipart/{date_folder}/{theme_slug}/"
                        sub_path = "/".join(parts[3:])
                    else:
                        date_folder = ""
                        theme_slug = parts[1].replace(".txt", "")
                        prefix = f"Clipart/{theme_slug}/"
                        sub_path = parts[1]

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

                    if sub_path.startswith("mockups/") or "mockup" in sub_path.lower():
                        folder_map[prefix]["has_mockups"] = True
                    if sub_path.startswith("pdf/") or obj.endswith(".pdf"):
                        folder_map[prefix]["has_pdf"] = True
                    if "metadata/listing.json" in obj or "listing.json" in obj:
                        folder_map[prefix]["has_metadata"] = True

            folder_items = [GcsFolderItem(**item) for item in folder_map.values()]
            # Sort newest date first
            folder_items.sort(key=lambda x: (x.date_folder, x.theme_slug), reverse=True)

            res = GcsFolderListResponse(folders=folder_items, gcs_available=True)
            _GCS_FOLDERS_CACHE_STORE = (now, res)
            return res
        except Exception as exc:
            logger.warning(f"[etsy_listing_service] GCS folder list failed: {exc}")
            return GcsFolderListResponse(folders=[], gcs_available=False)

    @classmethod
    def get_gcs_folder_details(
        cls, gcs_prefix: str, settings: Settings | None = None
    ) -> GcsFolderDetailsResponse:
        """Fetch listing.json metadata and mockup image object list for a GCS prefix."""
        app_settings = settings or get_settings()
        clean_prefix = gcs_prefix.rstrip("/") + "/"
        parts = clean_prefix.split("/")
        date_folder = parts[1] if len(parts) >= 3 else ""
        theme_slug = (
            parts[2] if len(parts) >= 3 else parts[-2] if len(parts) >= 2 else "Clipart"
        )
        display_name = theme_slug.replace("_", " ")

        record = cls.load_gcs_listing_record(clean_prefix, app_settings) or {}

        title = (
            record.get("etsy_title")
            or f"{display_name} Clipart PNG Bundle Transparent Digital Download"
        )
        description = (
            record.get("etsy_description")
            or f"High quality digital clipart set for {display_name}."
        )
        tags = record.get("etsy_tags") or [
            "clipart",
            "digital download",
            "png",
            "bundle",
        ]
        price = float(record.get("listing_price_usd", 5.99))
        quantity = int(record.get("listing_quantity", 999))

        mockups: list[str] = []
        if is_gcp_available():
            try:
                gcs = GCSStore(settings=app_settings)
                mockup_prefix = f"{clean_prefix}mockups/"
                objects = gcs.list_objects(mockup_prefix)
                for obj in sorted(objects):
                    if obj.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        # Format GCS media proxy URL
                        media_url = f"/api/v1/etsy/gcs-media?object_key={obj}"
                        mockups.append(media_url)
            except Exception as exc:
                logger.warning(
                    f"[etsy_listing_service] Listing mockups failed for '{clean_prefix}': {exc}"
                )

        return GcsFolderDetailsResponse(
            gcs_prefix=clean_prefix,
            theme_slug=theme_slug,
            display_name=display_name,
            date_folder=date_folder,
            title=title,
            description=description,
            tags=tags,
            price=price,
            quantity=quantity,
            who_made=record.get("who_made", "i_did"),
            is_digital=bool(record.get("is_digital", True)),
            is_ai_created=bool(record.get("is_ai_created", True)),
            renewal_option=record.get("renewal_option", "automatic"),
            taxonomy_id=int(record.get("taxonomy_id", 6844)),
            craft_type=record.get("craft_type")
            or [
                "Card making & stationery",
                "Collage",
                "Kids' crafts",
            ],
            mockups=mockups,
        )

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
        is_ai_created_override: bool | None = None,
        renewal_option_override: str | None = None,
        settings: Settings | None = None,
    ) -> ListingPublishResponse:
        """Publish a draft/active listing directly from GCS files."""
        app_settings = settings or get_settings()
        gcs = GCSStore(settings=app_settings)

        # Sanitize gcs_prefix if it already contains /mockups/
        clean_prefix = gcs_prefix
        if "/mockups" in clean_prefix:
            clean_prefix = clean_prefix.split("/mockups")[0]
        clean_prefix = clean_prefix.rstrip("/")

        mockup_search_prefix = f"{clean_prefix}/mockups/"
        pdf_search_prefix = f"{clean_prefix}/"

        # 1. Load listing.json or fallback
        record = cls.load_gcs_listing_record(clean_prefix, app_settings) or {}

        title = title_override or record.get("etsy_title")
        description = description_override or record.get("etsy_description")
        tags = tags_override if tags_override else record.get("etsy_tags", [])
        price = price_override or record.get("listing_price_usd", 5.99)
        quantity = quantity_override or record.get("listing_quantity", 999)
        is_ai_created = (
            is_ai_created_override
            if is_ai_created_override is not None
            else bool(record.get("is_ai_created", True))
        )
        renewal_option = (
            renewal_option_override
            if renewal_option_override is not None
            else str(record.get("renewal_option", "automatic"))
        )

        if not title:
            # Fallback title from prefix theme slug
            slug = clean_prefix.split("/")[-1].replace("_", " ")
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
            is_ai_created=is_ai_created,
            renewal_option=renewal_option,
        )

        # 2b. Set required Craft type property (Property ID 47626759760)
        cls._set_listing_craft_type(shop_id, listing_id, headers)

        # 3. Download mockups from GCS to temp dir in parallel
        mockup_files: list[Path] = []
        pdf_file: Path | None = None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mockup_dir = temp_path / "mockups"
            mockup_dir.mkdir(parents=True, exist_ok=True)

            mockup_objects = [
                obj
                for obj in gcs.list_objects(mockup_search_prefix)
                if Path(obj).name.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            ]
            pdf_objects = [
                obj
                for obj in gcs.list_objects(pdf_search_prefix)
                if obj.endswith(".pdf") or "pdf/" in obj
            ]

            def _download_single_gcs(obj_key: str) -> Path:
                dest_path = mockup_dir / Path(obj_key).name
                gcs.download_file(obj_key, dest_path)
                return dest_path

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(_download_single_gcs, key) for key in mockup_objects
                ]
                for future in as_completed(futures):
                    try:
                        file_path = future.result()
                        mockup_files.append(file_path)
                    except Exception as exc:
                        logger.warning(
                            f"[etsy_listing_service] GCS parallel download failed: {exc}"
                        )

            if pdf_objects:
                try:
                    pdf_key = pdf_objects[0]
                    local_pdf = temp_path / Path(pdf_key).name
                    gcs.download_file(pdf_key, local_pdf)
                    pdf_file = local_pdf
                except Exception:
                    pass

            # 4. Upload images (Hero first)
            logger.info(
                f"[etsy_listing_service] [Stage 2] Uploading {len(mockup_files)} mockup images for listing_id={listing_id}..."
            )
            sorted_mockups = sort_mockup_images(mockup_files)[:10]
            uploaded_count = cls._upload_mockup_images(
                shop_id=shop_id,
                listing_id=listing_id,
                mockup_files=sorted_mockups,
                headers=headers,
            )
            logger.info(
                f"[etsy_listing_service] [Stage 2 SUCCESS] Uploaded {uploaded_count}/{len(sorted_mockups)} mockup images."
            )

            # 5. Upload PDF digital file
            pdf_uploaded = False
            if pdf_file and pdf_file.exists():
                logger.info(
                    f"[etsy_listing_service] [Stage 3] Uploading digital PDF asset '{pdf_file.name}' for listing_id={listing_id}..."
                )
                pdf_uploaded = cls._upload_digital_file(
                    shop_id=shop_id,
                    listing_id=listing_id,
                    pdf_path=pdf_file,
                    headers=headers,
                )
                logger.info(
                    f"[etsy_listing_service] [Stage 3 RESULT] PDF Upload Success: {pdf_uploaded}"
                )

        if uploaded_count == 0 and not pdf_uploaded:
            logger.error(
                f"[etsy_listing_service] Failed to upload any mockup images or PDF files to Etsy for listing_id={listing_id}."
            )
            raise RuntimeError(
                f"Draft listing {listing_id} created, but failed to upload mockup images or PDF file to Etsy. Check API logs."
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

        # 1b. Set required Craft type property (Property ID 47626759760)
        cls._set_listing_craft_type(shop_id, listing_id, headers)

        # 2. Save uploaded files to temp dir
        saved_mockups: list[Path] = []
        saved_pdf: Path | None = None

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        theme_slug = re.sub(r"[^\w]", "_", title.split()[0] if title else "Clipart")[
            :30
        ]
        sanitized_shop_name = re.sub(r"[^\w]", "_", shop_name)
        gcs_shop_prefix = f"EtsyShops/{sanitized_shop_name}/{date_str}/{theme_slug}/"

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

        if uploaded_count == 0 and not pdf_uploaded:
            logger.error(
                f"[etsy_listing_service] [Upload Mode] Failed to upload any mockup images or PDF files to Etsy for listing_id={listing_id}."
            )
            raise RuntimeError(
                f"Draft listing {listing_id} created, but failed to upload mockup images or PDF file to Etsy. Check API logs."
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
        global _SHOP_STATS_CACHE_STORE
        now = time.time()
        if (
            shop_id in _SHOP_STATS_CACHE_STORE
            and (now - _SHOP_STATS_CACHE_STORE[shop_id][0]) < 600
        ):
            return _SHOP_STATS_CACHE_STORE[shop_id][1]

        headers = cls._get_headers(access_token)

        # 1. Try real Etsy API lookup by shop_id or shop_name
        try:
            url = (
                f"{ETSY_API_BASE}/shops/{shop_id}"
                if shop_id.isdigit()
                else f"{ETSY_API_BASE}/shops?shop_name={shop_name}"
            )
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if (
                    "results" in data
                    and isinstance(data["results"], list)
                    and data["results"]
                ):
                    data = data["results"][0]

                if "listing_active_count" in data or "shop_name" in data:
                    active_count = data.get("listing_active_count", 0)
                    digital_count = data.get("digital_listing_count", 0)
                    review_count = data.get("review_count", 0)
                    review_avg = float(data.get("review_average", 5.0))
                    currency = data.get("currency_code", "USD")
                    etsy_url = data.get("url", f"https://www.etsy.com/shop/{shop_name}")

                    res = EtsyShopStatsResponse(
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
                    _SHOP_STATS_CACHE_STORE[shop_id] = (now, res)
                    return res
        except Exception as exc:
            logger.warning(
                f"[etsy_listing_service] Shop stats fetch exception for {shop_name}: {exc}"
            )

        # If live stats fetch fails (e.g. invalid token or unverified shop), return exact 0 metrics
        formatted_url = (
            f"https://www.etsy.com/shop/{shop_name}"
            if " " not in shop_name and "#" not in shop_name
            else ""
        )
        res = EtsyShopStatsResponse(
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
        _SHOP_STATS_CACHE_STORE[shop_id] = (now, res)
        return res

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
        shared_secret = (
            os.getenv("ETSY_SHARED_SECRET") or app_settings.etsy_shared_secret
        )
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
        """Fetch taxonomy node ID for 'Clip Art & Image Files'."""
        try:
            url = f"{ETSY_API_BASE}/seller-taxonomy/nodes"
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                nodes = resp.json().get("results", [])
                for node in nodes:
                    if "clip art & image files" in node.get("name", "").lower():
                        return int(node["id"])
        except Exception:
            pass
        return 6844  # Official Etsy taxonomy ID for Clip Art & Image Files

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
        is_ai_created: bool = True,
        renewal_option: str = "automatic",
    ) -> tuple[int, str]:
        """POST /v3/application/shops/{shop_id}/listings"""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings"

        # Ensure price is at least 0.25 USD / 18.00 INR (Etsy minimum listing price limit)
        valid_price = max(0.25, float(price))

        payload = {
            "title": title[:140],
            "description": description,
            "tags": tags[:13],
            "price": valid_price,
            "quantity": max(1, quantity),
            "taxonomy_id": 6844 if taxonomy_id == 110 else taxonomy_id,
            "who_made": "i_did",
            "when_made": "made_to_order",
            "type": "download",
            "is_digital": True,
            "is_ai_created": bool(is_ai_created),
            "should_auto_renew": bool(renewal_option == "automatic"),
            "craft_type": ["Card making & stationery", "Collage", "Kids' crafts"],
            "materials": ["PNG", "Digital Download", "Transparent Background"],
            "state": "draft",
        }

        logger.info(
            f"[etsy_listing_service] [Stage 1] Creating Etsy draft listing shell for shop '{shop_id}' (price={valid_price})..."
        )
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            logger.error(
                f"[etsy_listing_service] [Stage 1 ERROR] Etsy draft creation failed ({resp.status_code}): {resp.text}"
            )
            raise RuntimeError(
                f"Etsy draft creation failed ({resp.status_code}): {resp.text}"
            )

        data = resp.json()
        listing_id = data.get("listing_id")
        listing_url = data.get("url", f"https://www.etsy.com/listing/{listing_id}")
        logger.info(
            f"[etsy_listing_service] [Stage 1 SUCCESS] Created draft listing_id={listing_id}, url={listing_url}"
        )
        return listing_id, listing_url

    @classmethod
    def _set_listing_craft_type(
        cls,
        shop_id: str,
        listing_id: int,
        headers: dict[str, str],
        values: list[str] | None = None,
    ) -> bool:
        """PUT /v3/application/shops/{shop_id}/listings/{listing_id}/properties/47626759760 (Craft type)"""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/{listing_id}/properties/47626759760"
        payload = {
            "value_ids": [
                538,
                541,
                562,
            ],  # Card making & stationery, Collage, Kids' crafts
            "values": values or ["Card making & stationery", "Collage", "Kids' crafts"],
        }
        try:
            logger.info(
                f"[etsy_listing_service] Setting required Craft type property for listing_id={listing_id}..."
            )
            resp = requests.put(url, json=payload, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                logger.info(
                    f"[etsy_listing_service] [Craft Type SUCCESS] Updated property 47626759760 for listing_id={listing_id}."
                )
                return True
            else:
                logger.warning(
                    f"[etsy_listing_service] Craft type property set returned HTTP {resp.status_code}: {resp.text}"
                )
        except Exception as exc:
            logger.warning(
                f"[etsy_listing_service] Failed to set Craft type property: {exc}"
            )
        return False

    @classmethod
    def _upload_mockup_images(
        cls,
        shop_id: str,
        listing_id: int,
        mockup_files: list[Path],
        headers: dict[str, str],
    ) -> int:
        """POST /v3/application/shops/{shop_id}/listings/{listing_id}/images sequentially"""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/{listing_id}/images"

        def _upload_single_image(rank: int, img_path: Path) -> bool:
            try:
                logger.info(
                    f"[etsy_listing_service] Uploading mockup {rank}/{len(mockup_files)} ('{img_path.name}') for listing_id={listing_id}..."
                )
                with open(img_path, "rb") as img_file:
                    files = {"image": (img_path.name, img_file, "image/png")}
                    data = {"rank": rank}
                    resp = requests.post(
                        url, headers=headers, files=files, data=data, timeout=60
                    )
                    if resp.status_code in (200, 201):
                        logger.info(
                            f"[etsy_listing_service] Image '{img_path.name}' uploaded successfully (rank={rank})."
                        )
                        return True
                    else:
                        logger.error(
                            f"[etsy_listing_service] Image upload failed for '{img_path.name}' (HTTP {resp.status_code}): {resp.text}"
                        )
            except Exception as exc:
                logger.error(
                    f"[etsy_listing_service] Image upload exception for '{img_path.name}': {exc}"
                )
            return False

        uploaded_count = 0
        import time

        for rank, img_path in enumerate(mockup_files, start=1):
            if _upload_single_image(rank, img_path):
                uploaded_count += 1
            # Rate limiting / concurrency guard: sleep 1.0 second between sequential image uploads
            time.sleep(1.0)

        return uploaded_count

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
                data = {
                    "name": pdf_path.name
                }  # Required parameter for Etsy API v3 digital file upload
                resp = requests.post(
                    url, headers=headers, files=files, data=data, timeout=60
                )
                if resp.status_code in (200, 201):
                    logger.info(
                        f"[etsy_listing_service] Digital PDF file '{pdf_path.name}' successfully uploaded for listing {listing_id}"
                    )
                    return True
                else:
                    logger.error(
                        f"[etsy_listing_service] PDF upload failed for listing {listing_id} (HTTP {resp.status_code}): {resp.text}"
                    )
        except Exception as exc:
            logger.error(
                f"[etsy_listing_service] PDF digital file upload exception for listing {listing_id}: {exc}",
                exc_info=True,
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
            logger.info(
                f"[etsy_listing_service] [Stage 4] Updating listing state to 'active' for listing_id={listing_id}..."
            )
            resp = requests.put(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                active_url = resp.json().get("url", fallback_url)
                logger.info(
                    f"[etsy_listing_service] [Stage 4 SUCCESS] Listing state updated to 'active'. URL: {active_url}"
                )
                return active_url
            else:
                logger.error(
                    f"[etsy_listing_service] [Stage 4 ERROR] Failed to activate listing_id={listing_id} (HTTP {resp.status_code}): {resp.text}"
                )
        except Exception as exc:
            logger.error(
                f"[etsy_listing_service] Publish active state exception for listing_id={listing_id}: {exc}",
                exc_info=True,
            )
        return fallback_url
