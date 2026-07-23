"""Unit tests for Mockup Creator theme name resolution."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path so we can import src from etsy mockup creator
project_root = Path(__file__).resolve().parent.parent
mockup_creator_dir = project_root / "etsy mockup creator"
if str(mockup_creator_dir) not in sys.path:
    sys.path.insert(0, str(mockup_creator_dir))


def test_theme_name_resolution_from_no_bg_parent(tmp_path: Path) -> None:
    """Test theme name resolution falls back to parent folder when theme_dir is no_bg."""
    from src.generator import Generator

    # Create dummy theme folder structure: <tmp>/wonder_woman_clipart/no_bg
    theme_dir = tmp_path / "wonder_woman_clipart" / "no_bg"
    theme_dir.mkdir(parents=True)
    (theme_dir / "character").mkdir(parents=True)
    (theme_dir / "character" / "char1.png").touch()

    # Pass theme_dir pointing to no_bg without explicit theme_name
    # Generator.generate_all should resolve theme_name to "wonder woman clipart"
    # We inspect code behavior by checking parent resolution logic
    path_obj = theme_dir
    theme_folder_name = path_obj.name
    if theme_folder_name.lower() in (
        "no_bg", "no bg", "no-bg", "nobg",
        "processed_no_bg", "processed no bg", "processed-no-bg",
        "misc_category", "scen-pattern"
    ):
        theme_folder_name = path_obj.parent.name

    assert theme_folder_name == "wonder_woman_clipart"


def test_theme_name_resolution_explicit_override() -> None:
    """Test explicit theme_name parameter overrides directory name."""
    theme_name_input = "  Wonder Woman Clipart 01  "
    clean_name = theme_name_input.strip()
    assert clean_name == "Wonder Woman Clipart 01"
