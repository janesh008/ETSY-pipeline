"""Unit tests for LifestyleOrchestrator, ThemeClassifier, and SurfaceGroupIndex."""

from __future__ import annotations

import sys
from pathlib import Path

# Add 'etsy mockup creator' directory to sys.path
mockup_creator_dir = Path(__file__).resolve().parent.parent / "etsy mockup creator"
if str(mockup_creator_dir) not in sys.path:
    sys.path.insert(0, str(mockup_creator_dir))

from PIL import Image
import pytest

from rendering.compatibility.surface_group_index import SurfaceGroupIndex
from rendering.compatibility.theme_classifier import ThemeClassifier
from rendering.plugins.lifestyle_orchestrator import LifestyleOrchestrator


@pytest.fixture
def temp_asset_dir(tmp_path):
    """Fixture creating temporary PNG assets with character names."""
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()

    # Create synthetic RGBA character images
    img1 = Image.new("RGBA", (100, 100), (20, 20, 20, 255))
    img1.save(asset_dir / "theme_MAIN_CHARACTER_001.png")

    img2 = Image.new("RGBA", (100, 100), (200, 50, 50, 255))
    img2.save(asset_dir / "theme_SUB_CHARACTER_001.png")

    img3 = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    # Prop image (should be skipped by classifier priority)
    img3.save(asset_dir / "theme_PROP_001.png")

    return asset_dir


def test_character_sampling_priority(temp_asset_dir):
    """Verify sampling respects MAIN_CHARACTER > SUB_CHARACTER priority and skips PROPs."""
    sampled = ThemeClassifier.sample_character_images(temp_asset_dir, max_samples=10)

    names = [p.name for p in sampled]
    assert "theme_MAIN_CHARACTER_001.png" in names
    assert "theme_SUB_CHARACTER_001.png" in names
    assert "theme_PROP_001.png" not in names


def test_theme_classification(temp_asset_dir):
    """Verify theme classification result data structure."""
    res = ThemeClassifier.classify_theme(temp_asset_dir)

    assert res.theme_group in ("dark_art", "light_art", "colorful_art", "medium_art")
    assert isinstance(res.avg_brightness, float)
    assert isinstance(res.avg_saturation, float)


def test_surface_group_index():
    """Verify SurfaceGroupIndex indexes lifestyle products by group."""
    products_dir = mockup_creator_dir / "rendering" / "lifestyle_products"
    if not products_dir.exists():
        pytest.skip("lifestyle_products directory not found")

    index = SurfaceGroupIndex(products_dir)
    dark_surfaces = index.get_surfaces_for_group("dark_art")

    assert isinstance(dark_surfaces, list)
    assert len(dark_surfaces) > 0
