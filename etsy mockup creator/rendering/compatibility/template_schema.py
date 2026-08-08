"""Template Compatibility Metadata Schema & Validation Module.

Defines the structured schema for template metadata and enforces strict
validation without fallback or dummy data generation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


class MissingTemplateMetadataError(Exception):
    """Raised when a template JSON file is missing required compatibility metadata."""


class InvalidTemplateMetadataError(Exception):
    """Raised when template metadata fields fail validation."""


VALID_PRODUCT_TYPES = {"tshirt", "sweatshirt", "tote_bag", "mug", "poster", "pillow"}
VALID_BACKGROUND_TONES = {"light", "dark", "neutral", "textured"}
VALID_BRIGHTNESS = {"dark", "medium", "light"}
VALID_SATURATION = {"low", "medium", "high"}


@dataclass
class CompatibilityMetadata:
    """Dataclass holding compatibility metadata for a mockup template."""

    template_id: str
    product_type: str
    product_color: str
    background_tone: str
    lighting: str
    print_area: str
    print_area_ratio: float
    contrast_profile: str
    compatible_brightness: list[str]
    compatible_saturation: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata instance to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any], template_source: str = "") -> CompatibilityMetadata:
        """Parse and validate metadata from dictionary.

        Raises:
            InvalidTemplateMetadataError: If validation fails.
        """
        if not isinstance(data, dict):
            raise InvalidTemplateMetadataError(
                f"Compatibility metadata for '{template_source}' must be a dictionary, got {type(data).__name__}."
            )

        required_fields = [
            "template_id",
            "product_type",
            "product_color",
            "background_tone",
            "lighting",
            "print_area",
            "print_area_ratio",
            "contrast_profile",
            "compatible_brightness",
            "compatible_saturation",
        ]

        missing = [field for field in required_fields if field not in data or data[field] is None]
        if missing:
            raise InvalidTemplateMetadataError(
                f"Template metadata for '{template_source}' is missing required fields: {missing}"
            )

        prod_type = str(data["product_type"]).lower()
        if prod_type not in VALID_PRODUCT_TYPES:
            logger.warning(f"Unrecognized product_type '{prod_type}' in template '{template_source}'. Expected one of {VALID_PRODUCT_TYPES}")

        bg_tone = str(data["background_tone"]).lower()
        if bg_tone not in VALID_BACKGROUND_TONES:
            raise InvalidTemplateMetadataError(
                f"Invalid background_tone '{bg_tone}' in template '{template_source}'. Must be one of {VALID_BACKGROUND_TONES}"
            )

        comp_bright = [str(b).lower() for b in data["compatible_brightness"]]
        invalid_bright = [b for b in comp_bright if b not in VALID_BRIGHTNESS]
        if invalid_bright:
            raise InvalidTemplateMetadataError(
                f"Invalid compatible_brightness {invalid_bright} in template '{template_source}'. Allowed: {VALID_BRIGHTNESS}"
            )

        comp_sat = [str(s).lower() for s in data["compatible_saturation"]]
        invalid_sat = [s for s in comp_sat if s not in VALID_SATURATION]
        if invalid_sat:
            raise InvalidTemplateMetadataError(
                f"Invalid compatible_saturation {invalid_sat} in template '{template_source}'. Allowed: {VALID_SATURATION}"
            )

        return cls(
            template_id=str(data["template_id"]),
            product_type=prod_type,
            product_color=str(data["product_color"]).lower(),
            background_tone=bg_tone,
            lighting=str(data["lighting"]),
            print_area=str(data["print_area"]),
            print_area_ratio=float(data["print_area_ratio"]),
            contrast_profile=str(data["contrast_profile"]),
            compatible_brightness=comp_bright,
            compatible_saturation=comp_sat,
        )


def extract_template_metadata(template_json: dict[str, Any], file_path: str | Path) -> CompatibilityMetadata:
    """Extract and validate compatibility metadata from a template JSON dictionary.

    STRICT ERROR HANDLING: No fallback or dummy metadata is ever generated.

    Raises:
        MissingTemplateMetadataError: If 'compatibility_metadata' key is absent.
        InvalidTemplateMetadataError: If metadata fields are invalid.
    """
    path_str = str(file_path)
    if "compatibility_metadata" not in template_json:
        error_msg = (
            f"Template at '{path_str}' is missing the required 'compatibility_metadata' block. "
            f"Please run 'python -m etsy_mockup_creator.tools.generate_template_metadata' "
            f"to generate and attach valid metadata to this template."
        )
        logger.error(f"[TemplateSchema] {error_msg}")
        raise MissingTemplateMetadataError(error_msg)

    meta_dict = template_json["compatibility_metadata"]
    return CompatibilityMetadata.from_dict(meta_dict, template_source=path_str)
