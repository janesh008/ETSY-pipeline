import sys
from pathlib import Path
from PIL import Image
import numpy as np
import pytest

# Add 'etsy mockup creator' directory to sys.path
mockup_creator_dir = Path(__file__).resolve().parent.parent / "etsy mockup creator"
if str(mockup_creator_dir) not in sys.path:
    sys.path.insert(0, str(mockup_creator_dir))

from rendering.compatibility.clipart_analyzer import (
    ClipartAnalysisError,
    ClipartAnalyzer,
)


def create_synthetic_png(color_rgb: tuple[int, int, int], alpha_val: int = 255, size: tuple[int, int] = (200, 200)) -> Image.Image:
    """Create synthetic RGBA image with colored box on transparent background."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    box = Image.new("RGBA", (100, 100), (*color_rgb, alpha_val))
    img.paste(box, (50, 50))
    return img


def test_clipart_analyzer_black_artwork():
    """Verify analysis of black artwork."""
    img = create_synthetic_png((10, 10, 10))  # Almost black
    analysis = ClipartAnalyzer.analyze_clipart(img)

    assert analysis.brightness_category == "dark"
    assert analysis.average_brightness < 0.35
    assert "white" in analysis.preferred_product_colors
    assert "black" not in analysis.preferred_product_colors


def test_clipart_analyzer_white_artwork():
    """Verify analysis of white artwork."""
    img = create_synthetic_png((245, 245, 245))  # White/Light
    analysis = ClipartAnalyzer.analyze_clipart(img)

    assert analysis.brightness_category == "light"
    assert analysis.average_brightness > 0.70
    assert "black" in analysis.preferred_product_colors
    assert "white" not in analysis.preferred_product_colors


def test_clipart_analyzer_fully_transparent_error():
    """Verify error raised on fully transparent PNG."""
    empty_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    with pytest.raises(ClipartAnalysisError):
        ClipartAnalyzer.analyze_clipart(empty_img)
