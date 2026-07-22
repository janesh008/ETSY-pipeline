"""Etsy Upload Worker — phase 9 of the Etsy pipeline.

Communicates with Etsy Open API v3 to create draft listings, upload mockup
images (sorted Hero.png first), publish listings live, and save listing URLs.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from etsy_pipeline.utils.exceptions import PipelineError
from etsy_pipeline.utils.logging import get_logger

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.gcs_store import GCSStore

logger = get_logger(__name__)

ETSY_API_BASE: str = "https://api.etsy.com/v3/application"
ETSY_TOKEN_URL: str = "https://api.etsy.com/v3/public/oauth/token"


class EtsyUploadError(PipelineError):
    """Exception raised during Etsy listing upload stage."""


def sort_mockup_images(image_paths: list[Path]) -> list[Path]:
    """Sort mockup images such that Hero.png is always first, then remaining alphabetically."""
    return sorted(
        image_paths,
        key=lambda p: (0 if p.stem.lower() == "hero" else 1, p.name.lower()),
    )


class EtsyWorker:
    """Worker module for running live Etsy Open API v3 listing uploads."""

    STAGE_NAME: str = "etsy_upload"

    def __init__(
        self,
        settings: Settings,
        gcs_store: GCSStore | None = None,
    ) -> None:
        """Initialise EtsyWorker."""
        self._settings = settings
        self._gcs = gcs_store

    def run(self, job: Job) -> Job:
        """Upload listing to Etsy Open API v3 and set active status.

        Args:
            job: The Job instance with etsy_title, etsy_description, etsy_tags populated.

        Returns:
            Updated Job object with etsy_listing_id and etsy_listing_url.

        Raises:
            EtsyUploadError: If Etsy API calls fail.
        """
        logger.info(f"[etsy_upload] Starting Etsy upload for '{job.theme}'")
        stage = job.stages[self.STAGE_NAME]
        stage.mark_running()

        if not job.etsy_title or not job.etsy_description or not job.etsy_tags:
            error_msg = "Job metadata (title, description, tags) is incomplete — run metadata_worker first."
            logger.error(f"[etsy_upload] {error_msg}")
            stage.mark_failed(error_msg)
            job.add_error(error_msg)
            raise EtsyUploadError(error_msg, job_id=job.job_id)

        # 1. Refresh OAuth access token
        access_token = self._refresh_oauth_token()
        headers = {
            "x-api-key": self._settings.etsy_keystring,
            "Authorization": f"Bearer {access_token}",
        }

        shop_id = self._settings.etsy_shop_id
        if not shop_id:
            raise EtsyUploadError(
                "ETSY_SHOP_ID is not configured in settings.", job_id=job.job_id
            )

        # 2. Fetch taxonomy ID for 'Clip Art'
        taxonomy_id = self._get_clip_art_taxonomy_id(headers)

        # 3. Create Draft Listing
        listing_id, listing_url = self._create_draft_listing(
            shop_id=shop_id,
            job=job,
            taxonomy_id=taxonomy_id,
            headers=headers,
        )

        # 4. Upload Mockup Images (Hero first, max 10 images)
        local_mockups_dir = (
            Path(self._settings.output_root)
            / job.date_folder
            / job.theme_slug
            / "mockups"
        )
        self._ensure_mockups_local(job, local_mockups_dir)

        mockup_files = sort_mockup_images(
            list(local_mockups_dir.glob("*.png")) + list(local_mockups_dir.glob("*.jpg"))
        )[:10]

        self._upload_listing_images(
            shop_id=shop_id,
            listing_id=listing_id,
            mockup_files=mockup_files,
            headers=headers,
        )

        # 5. Publish Listing (state = active)
        listing_url = self._publish_listing(
            shop_id=shop_id,
            listing_id=listing_id,
            headers=headers,
            fallback_url=listing_url,
        )

        # 6. Save results to Job
        job.etsy_listing_id = str(listing_id)
        job.etsy_listing_url = listing_url

        stage.mark_completed()
        logger.info(
            f"[etsy_upload] ✅ Published Etsy listing for '{job.theme}': {listing_url}"
        )
        return job

    def _refresh_oauth_token(self) -> str:
        """Refresh Etsy OAuth access token using refresh_token."""
        keystring = self._settings.etsy_keystring
        refresh_token = self._settings.etsy_refresh_token

        if not keystring or not refresh_token:
            # Fall back to access token if available
            if self._settings.etsy_access_token:
                return self._settings.etsy_access_token
            raise EtsyUploadError("ETSY_KEYSTRING or ETSY_REFRESH_TOKEN is missing.")

        payload = {
            "grant_type": "refresh_token",
            "client_id": keystring,
            "refresh_token": refresh_token,
        }
        try:
            resp = requests.post(ETSY_TOKEN_URL, data=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                new_access_token = data.get("access_token", "")
                new_refresh_token = data.get("refresh_token", "")
                if new_access_token:
                    self._update_env_tokens(new_access_token, new_refresh_token)
                    return new_access_token
            logger.warning(
                f"[etsy_upload] Token refresh failed ({resp.status_code}): {resp.text}. Falling back to configured access token."
            )
        except Exception as exc:
            logger.warning(f"[etsy_upload] OAuth refresh exception: {exc}")

        return self._settings.etsy_access_token

    def _update_env_tokens(self, access_token: str, refresh_token: str) -> None:
        """Update .env file with new OAuth tokens."""
        env_path = self._settings.project_root / ".env"
        if not env_path.exists():
            return
        try:
            content = env_path.read_text(encoding="utf-8")

            def set_kv(c: str, k: str, v: str) -> str:
                lines = c.splitlines()
                found = False
                new_lines = []
                for line in lines:
                    if line.startswith(f"{k}="):
                        new_lines.append(f"{k}={v}")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"{k}={v}")
                return "\n".join(new_lines) + "\n"

            updated = set_kv(content, "ETSY_ACCESS_TOKEN", access_token)
            if refresh_token:
                updated = set_kv(updated, "ETSY_REFRESH_TOKEN", refresh_token)

            env_path.write_text(updated, encoding="utf-8")
        except Exception as exc:
            logger.warning(f"[etsy_upload] Failed to save updated tokens to .env: {exc}")

    def _get_clip_art_taxonomy_id(self, headers: dict[str, str]) -> int:
        """Fetch taxonomy node ID for 'Clip Art'."""
        try:
            url = f"{ETSY_API_BASE}/seller-taxonomy/nodes"
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                nodes = resp.json().get("results", [])
                for node in nodes:
                    if "clip art" in node.get("name", "").lower():
                        return int(node["id"])
        except Exception as exc:
            logger.warning(f"[etsy_upload] Failed to fetch seller taxonomy: {exc}")

        return 110  # Default taxonomy node ID for Clip Art

    def _create_draft_listing(
        self,
        shop_id: str,
        job: Job,
        taxonomy_id: int,
        headers: dict[str, str],
    ) -> tuple[int, str]:
        """POST /v3/application/shops/{shop_id}/listings — create draft listing."""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings"
        payload = {
            "title": job.etsy_title,
            "description": job.etsy_description,
            "tags": job.etsy_tags,
            "price": job.listing_price_usd,
            "quantity": job.listing_quantity,
            "taxonomy_id": taxonomy_id,
            "who_made": "i_did",
            "when_made": "made_to_order",
            "type": "download",
            "is_digital": True,
            "materials": ["PNG", "Digital Download", "Transparent Background"],
            "state": "draft",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code not in (200, 201):
                raise EtsyUploadError(
                    f"Create draft listing failed ({resp.status_code}): {resp.text}",
                    job_id=job.job_id,
                )

            data = resp.json()
            listing_id = data.get("listing_id")
            listing_url = data.get("url", f"https://www.etsy.com/listing/{listing_id}")
            logger.info(f"[etsy_upload] Created draft listing ID {listing_id}")
            return listing_id, listing_url
        except Exception as exc:
            if isinstance(exc, EtsyUploadError):
                raise
            raise EtsyUploadError(
                f"Etsy create draft listing call failed: {exc}", job_id=job.job_id
            ) from exc

    def _upload_listing_images(
        self,
        shop_id: str,
        listing_id: int,
        mockup_files: list[Path],
        headers: dict[str, str],
    ) -> None:
        """Upload mockup images to listing (Hero.png first)."""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/{listing_id}/images"

        for rank, img_path in enumerate(mockup_files, start=1):
            try:
                with open(img_path, "rb") as img_file:
                    files = {"image": (img_path.name, img_file, "image/png")}
                    data = {"rank": rank}
                    resp = requests.post(
                        url, headers=headers, files=files, data=data, timeout=60
                    )
                    if resp.status_code in (200, 201):
                        logger.info(
                            f"[etsy_upload] Uploaded image #{rank}: {img_path.name}"
                        )
                    else:
                        logger.warning(
                            f"[etsy_upload] Upload image #{rank} failed ({resp.status_code}): {resp.text}"
                        )
            except Exception as exc:
                logger.warning(
                    f"[etsy_upload] Exception uploading image {img_path.name}: {exc}"
                )

    def _publish_listing(
        self,
        shop_id: str,
        listing_id: int,
        headers: dict[str, str],
        fallback_url: str,
    ) -> str:
        """PATCH listing to state=active to publish."""
        url = f"{ETSY_API_BASE}/shops/{shop_id}/listings/{listing_id}"
        payload = {"state": "active"}

        try:
            resp = requests.patch(url, json=payload, headers=headers, timeout=30)
            if resp.status_code in (200, 201):
                data = resp.json()
                logger.info(f"[etsy_upload] Published listing ID {listing_id} active")
                return data.get("url", fallback_url)
            else:
                logger.warning(
                    f"[etsy_upload] Failed to activate listing ({resp.status_code}): {resp.text}"
                )
        except Exception as exc:
            logger.warning(f"[etsy_upload] Exception activating listing: {exc}")

        return fallback_url

    def _ensure_mockups_local(self, job: Job, mockups_dir: Path) -> None:
        """Ensure local mockups exist, downloading from GCS if needed."""
        if mockups_dir.exists() and list(mockups_dir.glob("*.png")):
            return

        gcs = self._get_gcs()
        if not gcs:
            return

        gcs_prefix = f"Clipart/{job.date_folder}/{job.theme_slug}/mockups/"
        objects = gcs.list_objects(gcs_prefix)
        if not objects:
            return

        mockups_dir.mkdir(parents=True, exist_ok=True)
        for obj_path in objects:
            relative = obj_path[len(gcs_prefix) :]
            local_target = mockups_dir / relative
            local_target.parent.mkdir(parents=True, exist_ok=True)
            if not local_target.exists():
                gcs.download_file(obj_path, local_target)

    def _get_gcs(self) -> GCSStore | None:
        """Lazy load GCSStore."""
        if self._gcs is None and self._settings.gcs_bucket:
            from etsy_pipeline.services.gcs_store import GCSStore

            try:
                self._gcs = GCSStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[etsy_upload] GCSStore init failed: {exc}")
        return self._gcs
