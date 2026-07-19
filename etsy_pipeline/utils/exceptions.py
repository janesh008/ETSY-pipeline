"""
Custom exceptions for the Etsy pipeline.

Every pipeline stage raises meaningful, specific exceptions.
The Pipeline orchestrator catches these to log failures and
update the Job status properly.
"""


class PipelineError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(self, message: str, stage: str | None = None, job_id: str | None = None):
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


class MetadataGenerationError(PipelineError):
    """Raised when Etsy metadata generation fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="metadata_generation", job_id=job_id)


class CSVGenerationError(PipelineError):
    """Raised when CSV generation fails."""

    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message, stage="csv_generation", job_id=job_id)


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
