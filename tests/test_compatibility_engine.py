import sys
from pathlib import Path

# Add 'etsy mockup creator' directory to sys.path
mockup_creator_dir = Path(__file__).resolve().parent.parent / "etsy mockup creator"
if str(mockup_creator_dir) not in sys.path:
    sys.path.insert(0, str(mockup_creator_dir))

from PIL import Image
import pytest

from rendering.compatibility.clipart_analyzer import ClipartAnalyzer
from rendering.compatibility.compatibility_engine import (
    CompatibilityEngine,
    NoCompatibleTemplateFoundError,
)
from rendering.compatibility.template_schema import (
    MissingTemplateMetadataError,
)


def create_art(color_rgb: tuple[int, int, int]) -> Image.Image:
    """Helper to create synthetic clipart image."""
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    art_box = Image.new("RGBA", (120, 120), (*color_rgb, 255))
    img.paste(art_box, (40, 40))
    return img


# Sample mockup templates
WHITE_TSHIRT_TEMPLATE = (
    "tshirt_white.json",
    {
        "name": "White T-Shirt",
        "compatibility_metadata": {
            "template_id": "tshirt_white",
            "product_type": "tshirt",
            "product_color": "white",
            "background_tone": "neutral",
            "lighting": "soft",
            "print_area": "center_chest",
            "print_area_ratio": 0.55,
            "contrast_profile": "dark_or_colorful_art",
            "compatible_brightness": ["dark", "medium"],
            "compatible_saturation": ["medium", "high", "low"],
        },
    },
)

BLACK_TSHIRT_TEMPLATE = (
    "tshirt_black.json",
    {
        "name": "Black T-Shirt",
        "compatibility_metadata": {
            "template_id": "tshirt_black",
            "product_type": "tshirt",
            "product_color": "black",
            "background_tone": "dark",
            "lighting": "dramatic",
            "print_area": "center_chest",
            "print_area_ratio": 0.55,
            "contrast_profile": "light_or_pastel_art",
            "compatible_brightness": ["light", "medium"],
            "compatible_saturation": ["low", "medium", "high"],
        },
    },
)


def test_black_artwork_prefers_white_template():
    """Case 1: Black artwork must select white template over black template."""
    black_art = create_art((15, 15, 15))
    analysis = ClipartAnalyzer.analyze_clipart(black_art)

    templates = [WHITE_TSHIRT_TEMPLATE, BLACK_TSHIRT_TEMPLATE]
    result = CompatibilityEngine.rank_templates(analysis, templates)

    assert result.selected_template_id == "tshirt_white"
    assert result.score > 0.70


def test_white_artwork_prefers_black_template():
    """Case 2: White artwork must select black template over white template."""
    white_art = create_art((245, 245, 245))
    analysis = ClipartAnalyzer.analyze_clipart(white_art)

    templates = [WHITE_TSHIRT_TEMPLATE, BLACK_TSHIRT_TEMPLATE]
    result = CompatibilityEngine.rank_templates(analysis, templates)

    assert result.selected_template_id == "tshirt_black"
    assert result.score > 0.70


def test_pastel_artwork_prefers_dark_template():
    """Case 3: Pastel artwork prefers dark/black surface template."""
    pastel_art = create_art((255, 220, 230))  # Light pastel pink
    analysis = ClipartAnalyzer.analyze_clipart(pastel_art)

    templates = [WHITE_TSHIRT_TEMPLATE, BLACK_TSHIRT_TEMPLATE]
    result = CompatibilityEngine.rank_templates(analysis, templates)

    assert result.selected_template_id == "tshirt_black"


def test_manual_override():
    """Verify manual override parameter forces template selection."""
    black_art = create_art((15, 15, 15))
    analysis = ClipartAnalyzer.analyze_clipart(black_art)

    templates = [WHITE_TSHIRT_TEMPLATE, BLACK_TSHIRT_TEMPLATE]
    result = CompatibilityEngine.rank_templates(
        analysis, templates, override_template_id="tshirt_black"
    )

    assert result.selected_template_id == "tshirt_black"
    assert result.score == 1.0


def test_missing_metadata_raises_error():
    """Verify strict MissingTemplateMetadataError when metadata block is absent."""
    invalid_template = ("invalid.json", {"name": "No Metadata Template"})
    black_art = create_art((15, 15, 15))
    analysis = ClipartAnalyzer.analyze_clipart(black_art)

    with pytest.raises(MissingTemplateMetadataError):
        CompatibilityEngine.rank_templates(analysis, [invalid_template])


def test_no_compatible_template_found_error():
    """Verify NoCompatibleTemplateFoundError when no template passes threshold."""
    white_art = create_art((250, 250, 250))  # Light artwork
    analysis = ClipartAnalyzer.analyze_clipart(white_art)

    # Only white template available (will fail contrast requirements for white art)
    templates = [WHITE_TSHIRT_TEMPLATE]

    with pytest.raises(NoCompatibleTemplateFoundError) as exc_info:
        CompatibilityEngine.rank_templates(analysis, templates, min_score_threshold=0.85)

    err = exc_info.value
    assert "Mockup surface not found" in str(err)
    assert "black" in err.required_surface_recommendation["recommended_product_colors"]
