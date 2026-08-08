"""Template Metadata Auto-Generator Utility.

Helper tool for auto-populating or updating the 'compatibility_metadata'
schema block inside template JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from etsy_pipeline.utils.logging import get_logger

from .template_schema import CompatibilityMetadata

logger = get_logger(__name__)


def auto_generate_metadata(
    template_path: str | Path,
    product_type: str = "tshirt",
    product_color: str = "white",
    background_tone: str = "neutral",
    lighting: str = "soft",
    print_area: str = "center_chest",
    print_area_ratio: float = 0.55,
    save: bool = True,
) -> dict[str, Any]:
    """Generate and attach compatibility metadata to a template JSON file.

    Args:
        template_path: Path to target template JSON file.
        product_type: Product category (e.g. tshirt, mug, poster).
        product_color: Surface color (e.g. white, black, cream).
        background_tone: Background tone (e.g. light, dark, neutral).
        lighting: Lighting style (e.g. soft, bright).
        print_area: Print region description.
        print_area_ratio: Approximate area fraction of print region.
        save: If True, writes updated JSON back to file.

    Returns:
        Updated template JSON dictionary.
    """
    path_obj = Path(template_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Template file not found at: {path_obj}")

    with open(path_obj, "r", encoding="utf-8") as f:
        template_data = json.load(f)

    template_id = path_obj.stem

    # Infer profiles based on product color & tone
    color_lower = product_color.lower()
    if color_lower in ("white", "cream", "light_grey", "pastel_pink", "light_blue"):
        contrast_profile = "dark_or_colorful_art"
        comp_brightness = ["dark", "medium"]
        comp_saturation = ["medium", "high", "low"]
    elif color_lower in ("black", "dark_charcoal", "navy", "deep_red", "dark_green"):
        contrast_profile = "light_or_pastel_art"
        comp_brightness = ["light", "medium"]
        comp_saturation = ["low", "medium", "high"]
    else:
        contrast_profile = "universal"
        comp_brightness = ["dark", "medium", "light"]
        comp_saturation = ["low", "medium", "high"]

    metadata = CompatibilityMetadata(
        template_id=template_id,
        product_type=product_type,
        product_color=color_lower,
        background_tone=background_tone,
        lighting=lighting,
        print_area=print_area,
        print_area_ratio=print_area_ratio,
        contrast_profile=contrast_profile,
        compatible_brightness=comp_brightness,
        compatible_saturation=comp_saturation,
    )

    template_data["compatibility_metadata"] = metadata.to_dict()

    if save:
        with open(path_obj, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2)
        logger.info(f"[MetadataGenerator] Successfully attached compatibility_metadata to {path_obj}")

    return template_data
