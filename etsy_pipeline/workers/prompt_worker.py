"""
PromptWorker — generates image generation prompts using Gemini 2.5 Flash.

This worker loads the SKILL.md system instruction, sends a theme-specific
user message to Gemini, and parses the structured response into a
section-organized dictionary of prompt strings.

The worker contains ALL prompt generation implementation. It exposes
exactly one public method: `run(job) -> job`.

Future agent compatibility:
    class PromptAgent:
        def execute(self, job):
            return PromptWorker().run(job)
"""

from __future__ import annotations

import re
from pathlib import Path

from google import genai
from google.genai import types

from etsy_pipeline.config.settings import Settings, get_settings
from etsy_pipeline.models.job import Job
from etsy_pipeline.utils.exceptions import (
    ConfigurationError,
    PromptGenerationError,
    PromptParsingError,
    PromptValidationError,
    SkillFileError,
)
from etsy_pipeline.utils.logging import get_logger
from etsy_pipeline.workers.prompt_worker_config import (
    COUNT_CLAUSE_TEMPLATE,
    GEMINI_2_5_FLASH_INPUT_PRICE_PER_TOKEN,
    GEMINI_2_5_FLASH_OUTPUT_PRICE_PER_TOKEN,
    INACTIVE_SECTION_MARKER,
    LOCKED_SECTIONS,
    MIN_PROMPTS_PER_SECTION,
    SECTIONS_CLAUSE_TEMPLATE,
    STYLE_CLAUSE_TEMPLATE,
    USER_MESSAGE_TEMPLATE,
)

logger = get_logger(__name__)


class PromptWorker:
    """
    Generates image generation prompts for Etsy clipart bundles.

    Uses the SKILL.md prompt-engineering skill as the Gemini system
    instruction to produce structured, section-organized prompts
    ready for ComfyUI image generation.

    Usage:
        worker = PromptWorker()
        job = worker.run(job)
        print(job.prompts)  # {'MAIN_CHARACTER': [...], 'PATTERN': [...], ...}
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the PromptWorker.

        Args:
            settings: Optional Settings override. Uses global settings if not provided.
        """
        self._settings = settings or get_settings()
        self._skill_content: str | None = None
        self._client: genai.Client | None = None

    def run(self, job: Job) -> Job:
        """
        Generate prompts for the given job.

        This is the single public entry point for prompt generation.
        It loads the SKILL.md, calls Gemini, parses the response,
        validates the output, and stores everything in the Job.

        Args:
            job: The Job object containing theme and event information.

        Returns:
            The updated Job with prompts populated.

        Raises:
            PromptGenerationError: If prompt generation fails for any reason.
        """
        stage = job.stages["prompt_generation"]
        stage.mark_running(worker_id="prompt_worker")
        job.status = job.status.RUNNING

        logger.info(
            "Starting prompt generation",
            extra={"job_id": job.job_id, "theme": job.theme},
        )

        try:
            # 1. Load the SKILL.md system instruction
            skill_content = self._load_skill_file()

            # 2. Build the user message
            user_message = self._build_user_message(job)
            logger.debug(f"User message: {user_message}")

            # 3. Call Gemini 2.5 Flash
            raw_response = self._call_gemini(skill_content, user_message, job)

            # 4. Store raw response for debugging/reference
            job.raw_prompt_text = raw_response

            # 5. Parse the response into sections
            prompts, roster = self._parse_response(raw_response)

            # 6. Validate parsed prompts
            self._validate_prompts(prompts, job.job_id)

            # 7. Store results in Job
            job.prompts = prompts
            job.character_roster = roster
            job.add_log(
                f"Prompt generation completed: {sum(len(p) for p in prompts.values())} prompts "
                f"across {len([s for s, p in prompts.items() if p])} active sections"
            )

            stage.mark_completed()
            logger.info(
                f"Prompt generation completed: {job.total_prompt_count} prompts",
                extra={"job_id": job.job_id},
            )

        except (PromptGenerationError, PromptParsingError, PromptValidationError):
            # Re-raise pipeline-specific errors after logging
            raise

        except Exception as e:
            error_msg = f"Unexpected error during prompt generation: {e}"
            stage.mark_failed(error_msg)
            job.add_error(error_msg)
            logger.error(error_msg, exc_info=True, extra={"job_id": job.job_id})
            raise PromptGenerationError(error_msg, job_id=job.job_id) from e

        return job

    # -----------------------------------------------------------------
    # Private Methods
    # -----------------------------------------------------------------

    def _load_skill_file(self) -> str:
        """
        Load and cache the SKILL.md content, stripping YAML frontmatter.

        Returns:
            The SKILL.md content without frontmatter.

        Raises:
            SkillFileError: If the file cannot be found or read.
        """
        if self._skill_content is not None:
            return self._skill_content

        skill_path = Path(self._settings.skill_file_path)

        if not skill_path.exists():
            raise SkillFileError(
                f"SKILL.md not found at: {skill_path}. "
                f"Set SKILL_FILE_PATH in your .env or environment."
            )

        try:
            raw_content = skill_path.read_text(encoding="utf-8")
        except Exception as e:
            raise SkillFileError(f"Failed to read SKILL.md: {e}") from e

        # Strip YAML frontmatter (content between --- markers at the start)
        content = self._strip_frontmatter(raw_content)

        if not content.strip():
            raise SkillFileError("SKILL.md is empty after stripping frontmatter.")

        self._skill_content = content
        logger.debug(f"Loaded SKILL.md ({len(content)} chars) from {skill_path}")
        return content

    def _strip_frontmatter(self, content: str) -> str:
        """
        Remove YAML frontmatter from markdown content.

        Frontmatter is delimited by `---` at the start and end.
        """
        pattern = r"^---\s*\n.*?\n---\s*\n"
        return re.sub(pattern, "", content, count=1, flags=re.DOTALL)

    def _build_user_message(self, job: Job) -> str:
        """
        Build the user message for Gemini from the Job's theme parameters.

        Args:
            job: The Job containing theme, event_type, and optional overrides.

        Returns:
            Formatted user message string.
        """
        style_clause = ""
        if job.style_hint:
            style_clause = STYLE_CLAUSE_TEMPLATE.format(style_hint=job.style_hint)

        count_clause = ""
        if job.prompt_count:
            count_clause = COUNT_CLAUSE_TEMPLATE.format(prompt_count=job.prompt_count)

        sections_clause = ""
        if job.sections_requested:
            sections_clause = SECTIONS_CLAUSE_TEMPLATE.format(
                sections=", ".join(job.sections_requested)
            )

        return USER_MESSAGE_TEMPLATE.format(
            theme=job.theme,
            event_type=job.event_type,
            style_clause=style_clause,
            count_clause=count_clause,
            sections_clause=sections_clause,
        )

    def _get_client(self) -> genai.Client:
        """
        Get or create the Gemini client.

        Connects exclusively to Vertex AI (using GCP Application Default Credentials
        or a locally configured Service Account JSON file).

        Returns:
            Configured genai.Client instance.

        Raises:
            ConfigurationError: If required GCP configuration is missing.
        """
        if self._client is not None:
            return self._client

        project = self._settings.gcp_project_id
        location = self._settings.gcp_location

        if not project:
            raise ConfigurationError(
                "GCP_PROJECT_ID is not configured. Add it to your .env file."
            )

        logger.info(
            f"Initializing Vertex AI client (project={project}, location={location})"
        )
        self._client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        return self._client

    def _call_gemini(self, system_instruction: str, user_message: str, job: Job) -> str:
        """
        Call Gemini 2.5 Flash with the SKILL.md system instruction.

        Tracks input/output token usage and estimates Vertex AI billing cost.

        Args:
            system_instruction: The SKILL.md content as system instruction.
            user_message: The user's theme-specific message.
            job: The Job for logging context.

        Returns:
            The raw text response from Gemini.

        Raises:
            PromptGenerationError: If the API call fails.
        """
        client = self._get_client()
        model = self._settings.gemini_model

        logger.info(
            f"Calling Gemini ({model})",
            extra={"job_id": job.job_id},
        )

        try:
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self._settings.gemini_temperature,
                    max_output_tokens=self._settings.gemini_max_output_tokens,
                ),
            )

            if not response.text:
                raise PromptGenerationError(
                    "Gemini returned an empty response.",
                    job_id=job.job_id,
                )

            # --- Token Consumption & Cost Tracking ---
            input_tokens = 0
            output_tokens = 0
            estimated_cost = 0.0

            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0

                # Calculate estimated cost based on rates in prompt_worker_config
                estimated_cost = (
                    input_tokens * GEMINI_2_5_FLASH_INPUT_PRICE_PER_TOKEN
                ) + (output_tokens * GEMINI_2_5_FLASH_OUTPUT_PRICE_PER_TOKEN)

            logger.info(
                f"Gemini response received: {len(response.text)} chars. "
                f"Tokens consumed: {input_tokens} input, {output_tokens} output. "
                f"Estimated billing cost: ${estimated_cost:.6f}",
                extra={"job_id": job.job_id},
            )

            # Store the billing/token metadata directly into the job's stage result metadata
            stage_result = job.stages.get("prompt_generation")
            if stage_result:
                stage_result.metadata["input_tokens"] = input_tokens
                stage_result.metadata["output_tokens"] = output_tokens
                stage_result.metadata["estimated_cost_usd"] = estimated_cost

            return response.text

        except PromptGenerationError:
            raise
        except Exception as e:
            raise PromptGenerationError(
                f"Gemini API call failed: {e}",
                job_id=job.job_id,
            ) from e

    def _parse_response(
        self, raw_text: str
    ) -> tuple[dict[str, list[str]], dict[str, str]]:
        """
        Parse the raw Gemini response into section-organized prompts.

        The SKILL.md output format uses locked section headings (## SECTION_NAME)
        with numbered prompts underneath. Inactive sections have a marker note.

        Args:
            raw_text: The raw text response from Gemini.

        Returns:
            A tuple of:
            - prompts: dict mapping section name -> list of prompt strings
            - roster: dict mapping character slot -> description (if found)

        Raises:
            PromptParsingError: If the response cannot be parsed.
        """
        prompts: dict[str, list[str]] = {}
        roster: dict[str, str] = {}

        # Split by section headings (## SECTION_NAME)
        # This regex matches "## " followed by a locked section name
        section_pattern = re.compile(
            r"^##\s+(" + "|".join(re.escape(s) for s in LOCKED_SECTIONS) + r")\s*$",
            re.MULTILINE,
        )

        # Find all section positions
        matches = list(section_pattern.finditer(raw_text))

        if not matches:
            raise PromptParsingError(
                "No valid section headings found in the Gemini response. "
                "Expected headings like '## MAIN_CHARACTER', '## PATTERN', etc."
            )

        # Extract content between sections
        for i, match in enumerate(matches):
            section_name = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)

            section_content = raw_text[start:end].strip()

            # Check if section is marked inactive
            if INACTIVE_SECTION_MARKER in section_content.lower().replace("—", "-"):
                prompts[section_name] = []
                continue

            # Also check for exact marker
            if "(not applicable" in section_content.lower():
                prompts[section_name] = []
                continue

            # Extract numbered prompts from the section content
            section_prompts = self._extract_prompts_from_section(section_content)
            prompts[section_name] = section_prompts

        # Try to extract character roster from the text before the first section
        if matches:
            preamble = raw_text[: matches[0].start()]
            roster = self._extract_roster(preamble)

        # Ensure all locked sections are present (even if not in the response)
        for section in LOCKED_SECTIONS:
            if section not in prompts:
                prompts[section] = []

        logger.debug(
            f"Parsed {sum(len(p) for p in prompts.values())} prompts "
            f"across {len([s for s, p in prompts.items() if p])} active sections"
        )

        return prompts, roster

    def _extract_prompts_from_section(self, section_content: str) -> list[str]:
        """
        Extract individual prompts from a section's content.

        Prompts are numbered lines (e.g., "1. prompt text here...").
        Multi-line prompts are joined back into single strings.

        Args:
            section_content: The text content of a single section.

        Returns:
            List of prompt strings.
        """
        prompts: list[str] = []

        # Match numbered prompts: "1. ", "2. ", etc.
        # A numbered prompt starts at a line beginning with digits followed by a period
        prompt_pattern = re.compile(r"^\d+\.\s+", re.MULTILINE)

        # Find all prompt start positions
        prompt_starts = list(prompt_pattern.finditer(section_content))

        for i, match in enumerate(prompt_starts):
            # Start after the number prefix (e.g., after "1. ")
            start = match.end()
            # End at the next numbered prompt or end of section
            end = (
                prompt_starts[i + 1].start()
                if i + 1 < len(prompt_starts)
                else len(section_content)
            )

            prompt_text = section_content[start:end].strip()

            # Join multi-line prompts into a single line
            prompt_text = " ".join(prompt_text.split())

            if prompt_text:
                prompts.append(prompt_text)

        return prompts

    def _extract_roster(self, preamble: str) -> dict[str, str]:
        """
        Extract the character roster from the preamble text.

        The SKILL.md instructs Gemini to write out the roster before
        generating prompts, in the format:
            MAIN_CHARACTER: Stitch — blue alien with large ears
            SUB_CHARACTER_1: Lilo — Hawaiian girl, red floral dress

        Args:
            preamble: Text before the first section heading.

        Returns:
            Dict mapping character slot name to character description.
        """
        roster: dict[str, str] = {}
        roster_pattern = re.compile(
            r"(MAIN_CHARACTER|SUB_CHARACTER_\d)\s*:\s*(.+)",
            re.MULTILINE,
        )
        for match in roster_pattern.finditer(preamble):
            slot_name = match.group(1)
            description = match.group(2).strip()
            roster[slot_name] = description

        return roster

    def _validate_prompts(
        self,
        prompts: dict[str, list[str]],
        job_id: str | None = None,
    ) -> None:
        """
        Validate parsed prompts against SKILL.md rules.

        Checks:
        - All locked section headings are present
        - Active sections meet the minimum prompt count (RULE E)
        - Prompts are non-empty strings

        Args:
            prompts: The parsed prompts dictionary.
            job_id: Optional job ID for error context.

        Raises:
            PromptValidationError: If validation fails.
        """
        warnings: list[str] = []

        # Check all locked sections are present
        missing_sections = set(LOCKED_SECTIONS) - set(prompts.keys())
        if missing_sections:
            logger.warning(
                f"Missing sections in output (added as empty): {missing_sections}"
            )
            for section in missing_sections:
                prompts[section] = []

        # Check minimum prompt count for active sections
        for section_name, section_prompts in prompts.items():
            if not section_prompts:
                continue  # Skip inactive sections

            if len(section_prompts) < MIN_PROMPTS_PER_SECTION:
                warnings.append(
                    f"Section '{section_name}' has {len(section_prompts)} prompts "
                    f"(minimum is {MIN_PROMPTS_PER_SECTION})"
                )

            # Check for empty prompts
            empty_count = sum(1 for p in section_prompts if not p.strip())
            if empty_count > 0:
                warnings.append(
                    f"Section '{section_name}' has {empty_count} empty prompt(s)"
                )

        # Log warnings but don't fail — Gemini output may occasionally
        # fall slightly below the floor for smaller themes
        if warnings:
            for warning in warnings:
                logger.warning(warning, extra={"job_id": job_id})

        total = sum(len(p) for p in prompts.values())
        if total == 0:
            raise PromptValidationError(
                "No prompts were extracted from the Gemini response.",
                job_id=job_id,
            )

        logger.info(f"Prompt validation passed: {total} total prompts")


def generate_prompts(job: Job) -> Job:
    """
    Module-level entry point for prompt generation.

    This is the single public function exposed by this module,
    as required by the pipeline architecture.

    Args:
        job: The Job object containing theme and event information.

    Returns:
        The updated Job with prompts populated.
    """
    worker = PromptWorker()
    return worker.run(job)
