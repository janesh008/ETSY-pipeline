"""
Custom exceptions for the Etsy pipeline.

Every pipeline stage raises meaningful, specific exceptions.
The Pipeline orchestrator catches these to log failures and
update the Job status properly.
"""


class PipelineError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(
        self, message: str, stage: str | None = None, job_id: str | None = None
    ):
        self.stage = stage
        self.job_id = job_id
        super().__init__(message)

    def __str__(self) -> str:
        parts = []
        if self.stage:
            parts.append(f"[{self.stage}]")
        if self.job_id:
            parts.append(f"(job={self.job_id})")
        parts.append(super().__str__())
        return " ".join(parts)


# --- Stage-Specific Exceptions ---


class PromptGenerationError(PipelineError):
    """Raised when prompt generation fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="prompt_generation", job_id=job_id)


class PromptParsingError(PromptGenerationError):
    """Raised when the raw Gemini response cannot be parsed into sections."""

    pass


class PromptValidationError(PromptGenerationError):
    """Raised when parsed prompts fail validation (missing sections, too few prompts, etc.)."""

    pass


class ImageGenerationError(PipelineError):
    """Raised when image generation via ComfyUI fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="image_generation", job_id=job_id)


class BackgroundRemovalError(PipelineError):
    """Raised when background removal via rembg fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="bg_removal", job_id=job_id)


class UpscalingError(PipelineError):
    """Raised when image upscaling fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="upscaling", job_id=job_id)


class MockupGenerationError(PipelineError):
    """Raised when mockup generation fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="mockups", job_id=job_id)


class RenderingPluginError(MockupGenerationError):
    """Raised when a specific rendering plugin (hero, lifestyle, etc.) fails."""

    def __init__(self, plugin_name: str, message: str, job_id: str | None = None):
        self.plugin_name = plugin_name
        super().__init__(f"Plugin '{plugin_name}' failed: {message}", job_id=job_id)


class MetadataGenerationError(PipelineError):
    """Raised when Etsy metadata generation fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="metadata_generation", job_id=job_id)


class CSVGenerationError(PipelineError):
    """Raised when CSV generation fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="csv_generation", job_id=job_id)


class ListingRecordError(PipelineError):
    """Raised when per-theme listing.json record generation fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="listing_record", job_id=job_id)


class EtsyUploadError(PipelineError):
    """Raised when Etsy listing upload fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="etsy_upload", job_id=job_id)


class ConfigurationError(PipelineError):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str):
        super().__init__(message, stage="configuration")


class SkillFileError(PipelineError):
    """Raised when the SKILL.md file cannot be loaded or parsed."""

    def __init__(self, message: str):
        super().__init__(message, stage="skill_loading")


class InsufficientMockupCoverageError(PipelineError):
    """Raised when lifestyle mockup surface coverage is below threshold (< 6 surfaces)."""

    def __init__(
        self,
        theme_slug: str,
        theme_group: str,
        surfaces_available: int,
        surfaces_needed: int = 6,
        missing_surface_specs: list[dict] | None = None,
        job_id: str | None = None,
    ):
        message = (
            f"Insufficient lifestyle surface coverage for theme '{theme_slug}' (group: '{theme_group}'): "
            f"{surfaces_available}/{surfaces_needed} surfaces available."
        )
        super().__init__(message, stage="mockups", job_id=job_id)
        self.theme_slug = theme_slug
        self.theme_group = theme_group
        self.surfaces_available = surfaces_available
        self.surfaces_needed = surfaces_needed
        self.missing_surface_specs = missing_surface_specs or []


class MissingSurfaceGroupError(PipelineError):
    """Raised when a lifestyle product surface metadata.json is missing compatibility_groups."""

    def __init__(self, surface_name: str, metadata_path: str):
        message = (
            f"Lifestyle product surface '{surface_name}' at {metadata_path} "
            "is missing required 'compatibility_groups' field in metadata.json."
        )
        super().__init__(message, stage="mockups")
        self.surface_name = surface_name
        self.metadata_path = metadata_path
