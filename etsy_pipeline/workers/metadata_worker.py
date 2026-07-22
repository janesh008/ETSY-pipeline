"""Metadata Generation Worker — phase 8 of the Etsy pipeline.

Generates SEO-optimized Etsy listing title, description, and 13 tags
using Gemini 2.5 Flash Vision fed with mockup PNG images and the master
Etsy listing prompt.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from google import genai
from google.genai import types

from etsy_pipeline.utils.exceptions import PipelineError
from etsy_pipeline.utils.logging import get_logger
from etsy_pipeline.workers.metadata_worker_config import (
    DESCRIPTION_MAX_CHARS,
    GEMINI_MODEL,
    MASTER_PROMPT_PATH,
    TAG_COUNT,
    TAG_MAX_CHARS,
    TITLE_INVALID_CHARS_RE,
    TITLE_MAX_CHARS,
    TITLE_RESTRICTED_ONCE,
)

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job
    from etsy_pipeline.services.gcs_store import GCSStore
    from etsy_pipeline.services.mongo_store import MongoJobStore

logger = get_logger(__name__)


class MetadataGenerationError(PipelineError):
    """Exception raised during metadata generation stage."""


class MetadataWorker:
    """Worker for generating Etsy listing metadata using Gemini Vision."""

    STAGE_NAME: str = "metadata_generation"

    def __init__(
        self,
        settings: Settings,
        mongo_store: MongoJobStore | None = None,
        gcs_store: GCSStore | None = None,
        client: genai.Client | None = None,
    ) -> None:
        """Initialise MetadataWorker."""
        self._settings = settings
        self._mongo = mongo_store
        self._gcs = gcs_store
        self._client = client

    def run(self, job: Job) -> Job:
        """Run Etsy listing metadata generation for a Job.

        Args:
            job: Pipeline job context object.

        Returns:
            Updated Job instance.

        Raises:
            MetadataGenerationError: If metadata generation fails.
        """
        logger.info(f"[metadata] Starting metadata generation for '{job.theme}'")
        stage = job.stages[self.STAGE_NAME]
        stage.mark_running()
        start_time = datetime.now(UTC)

        local_base_dir = (
            Path(self._settings.output_root) / job.date_folder / job.theme_slug
        )
        mockups_dir = local_base_dir / "mockups"

        # 1. Download mockups from GCS if not present locally
        self._ensure_mockup_images_local(job, mockups_dir)

        mockup_files = sorted(
            list(mockups_dir.glob("*.png")) + list(mockups_dir.glob("*.jpg"))
        )
        if not mockup_files:
            error_msg = f"No mockup images found in {mockups_dir} to generate metadata."
            logger.error(f"[metadata] {error_msg}")
            stage.mark_failed(error_msg)
            job.add_error(error_msg)
            raise MetadataGenerationError(error_msg, job_id=job.job_id)

        # 2. Load Master Prompt
        system_instruction = self._load_master_prompt()

        # 3. Call Gemini Vision
        raw_response = self._call_gemini_vision(
            system_instruction=system_instruction,
            mockup_files=mockup_files,
            job=job,
        )

        # 4. Parse & Validate
        title, description, tags = self._parse_and_validate_response(raw_response)

        # 5. Populate Job fields
        job.etsy_title = title
        job.etsy_description = description
        job.etsy_tags = tags
        job.metadata = {
            "title": title,
            "description": description,
            "tags": tags,
            "raw_response_len": len(raw_response),
        }

        # 6. Upload raw Gemini response to GCS
        gcs = self._get_gcs()
        if gcs:
            try:
                temp_raw_file = local_base_dir / "raw_metadata_response.txt"
                temp_raw_file.write_text(raw_response, encoding="utf-8")
                gcs_raw_key = (
                    f"Clipart/{job.date_folder}/{job.theme_slug}/metadata/raw_response.txt"
                )
                gcs.upload_file(temp_raw_file, gcs_raw_key)
                if temp_raw_file.exists():
                    temp_raw_file.unlink()
            except Exception as exc:
                logger.warning(f"[metadata] Failed to upload raw response to GCS: {exc}")

        elapsed_hours = (datetime.now(UTC) - start_time).total_seconds() / 3600
        cost = round(elapsed_hours * 0.2, 4)

        stage.mark_completed(cost_usd=cost)
        logger.info(f"[metadata] Successfully generated Etsy metadata for '{job.theme}'")
        return job

    def _load_master_prompt(self) -> str:
        """Load Deepseek Etsy listing master prompt file."""
        prompt_path = self._settings.project_root / MASTER_PROMPT_PATH
        if not prompt_path.exists():
            raise MetadataGenerationError(
                f"Master prompt file not found at: {prompt_path}"
            )
        return prompt_path.read_text(encoding="utf-8")

    def _call_gemini_vision(
        self,
        system_instruction: str,
        mockup_files: list[Path],
        job: Job,
    ) -> str:
        """Call Gemini Vision model with mockup images."""
        client = self._get_client()
        model = self._settings.gemini_model or GEMINI_MODEL

        user_message = (
            f"Generate the complete Etsy listing for this clipart bundle theme: '{job.theme}'. "
            f"Event type: {job.event_type}."
        )

        contents: list[types.Part | str] = [user_message]
        for img_path in mockup_files[:5]:  # Send up to top 5 mockup previews
            try:
                img_bytes = img_path.read_bytes()
                mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
                part = types.Part.from_bytes(data=img_bytes, mime_type=mime)
                contents.append(part)
            except Exception as exc:
                logger.warning(f"[metadata] Could not read image {img_path}: {exc}")

        logger.info(
            f"[metadata] Calling Gemini Vision ({model}) with {len(contents) - 1} images..."
        )

        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self._settings.gemini_temperature,
                    max_output_tokens=self._settings.gemini_max_output_tokens,
                ),
            )
            if not response.text:
                raise MetadataGenerationError(
                    "Empty response returned from Gemini Vision", job_id=job.job_id
                )
            return response.text
        except Exception as exc:
            error_msg = f"Gemini Vision call failed: {exc}"
            logger.error(f"[metadata] {error_msg}")
            raise MetadataGenerationError(error_msg, job_id=job.job_id) from exc

    def _parse_and_validate_response(
        self, raw_text: str
    ) -> tuple[str, str, list[str]]:
        """Parse raw markdown output into validated Title, Description, and Tags."""
        # 1. Parse Title
        title_match = re.search(
            r"###\s*🏷️\s*ETSY TITLE\s*\n+`?([^`\n]+)`?", raw_text, re.IGNORECASE
        )
        if not title_match:
            title_match = re.search(r"ETSY TITLE[^\n]*\n+`?([^`\n]+)`?", raw_text, re.IGNORECASE)

        raw_title = title_match.group(1).strip() if title_match else "Digital Clipart Bundle PNG Clipart"
        title = self._validate_title(raw_title)

        # 2. Parse Description
        desc_match = re.search(
            r"###\s*📝\s*ETSY DESCRIPTION\s*\n+(.*?)(?=###\s*🔖|\Z)",
            raw_text,
            re.DOTALL | re.IGNORECASE,
        )
        raw_description = desc_match.group(1).strip() if desc_match else raw_text
        description = self._validate_description(raw_description)

        # 3. Parse Tags
        tags_match = re.search(
            r"###\s*🔖\s*ETSY TAGS[^\n]*\n+(.*?)(?=\Z)", raw_text, re.DOTALL | re.IGNORECASE
        )
        raw_tags_block = tags_match.group(1) if tags_match else raw_text
        raw_tag_lines = re.findall(
            r"^\s*\d+\.\s*([^(#\n]+?)(?:\s*\*|\s*$)", raw_tags_block, re.MULTILINE
        )

        tags = self._validate_tags(raw_tag_lines)

        return title, description, tags

    def _validate_title(self, title: str) -> str:
        """Sanitize and validate Etsy listing title."""
        clean_title = TITLE_INVALID_CHARS_RE.sub("", title).strip()

        # Check restricted once characters (% : & +)
        for char in TITLE_RESTRICTED_ONCE:
            if clean_title.count(char) > 1:
                parts = clean_title.split(char)
                clean_title = char.join(parts[:2]) + "".join(parts[2:])

        if len(clean_title) > TITLE_MAX_CHARS:
            clean_title = clean_title[:TITLE_MAX_CHARS].rstrip()

        return clean_title or "Digital Clipart PNG Bundle Set"

    def _validate_description(self, description: str) -> str:
        """Clean description HTML tags and validate length."""
        clean_desc = re.sub(r"<[^>]*>", "", description).strip()
        if len(clean_desc) > DESCRIPTION_MAX_CHARS:
            clean_desc = clean_desc[:DESCRIPTION_MAX_CHARS]
        return clean_desc

    def _validate_tags(self, raw_tags: list[str]) -> list[str]:
        """Validate tag list to ensure exactly 13 tags, each <= 20 chars."""
        cleaned_tags: list[str] = []
        seen: set[str] = set()

        for tag in raw_tags:
            clean_tag = re.sub(r"[^\w\s\-]", "", tag).strip()
            if len(clean_tag) > TAG_MAX_CHARS:
                clean_tag = clean_tag[:TAG_MAX_CHARS].strip()
            
            lower_tag = clean_tag.lower()
            if clean_tag and lower_tag not in seen:
                seen.add(lower_tag)
                cleaned_tags.append(clean_tag)

        # Fallback tags if fewer than 13
        fallback_pool = [
            "clipart bundle",
            "watercolor clipart",
            "digital download",
            "commercial png",
            "sublimation png",
            "party invitation",
            "nursery art png",
            "printable graphics",
            "craft asset pack",
            "instant download",
            "digital paper set",
            "diy craft supply",
            "pod design element",
        ]
        for fallback in fallback_pool:
            if len(cleaned_tags) >= TAG_COUNT:
                break
            if fallback.lower() not in seen:
                seen.add(fallback.lower())
                cleaned_tags.append(fallback[:TAG_MAX_CHARS])

        return cleaned_tags[:TAG_COUNT]

    def _ensure_mockup_images_local(self, job: Job, mockups_dir: Path) -> None:
        """Download mockups from GCS if not present locally."""
        gcs = self._get_gcs()
        if not gcs:
            return

        gcs_prefix = f"Clipart/{job.date_folder}/{job.theme_slug}/mockups/"
        objects = gcs.list_objects(gcs_prefix)
        if not objects:
            logger.warning(f"[metadata] No GCS mockups found under prefix {gcs_prefix}")
            return

        mockups_dir.mkdir(parents=True, exist_ok=True)
        for obj_path in objects:
            relative = obj_path[len(gcs_prefix) :]
            local_target = mockups_dir / relative
            local_target.parent.mkdir(parents=True, exist_ok=True)
            if not local_target.exists():
                gcs.download_file(obj_path, local_target)

    def _get_client(self) -> genai.Client:
        """Get or create Vertex AI genai client."""
        if self._client is not None:
            return self._client

        project = self._settings.gcp_project_id
        location = self._settings.gcp_location
        if not project:
            raise MetadataGenerationError("GCP_PROJECT_ID is not configured in settings.")

        self._client = genai.Client(vertexai=True, project=project, location=location)
        return self._client

    def _get_gcs(self) -> GCSStore | None:
        """Lazy load GCSStore."""
        if self._gcs is None and self._settings.gcs_bucket:
            from etsy_pipeline.services.gcs_store import GCSStore

            try:
                self._gcs = GCSStore(settings=self._settings)
            except Exception as exc:
                logger.warning(f"[metadata] GCSStore init failed: {exc}")
        return self._gcs
