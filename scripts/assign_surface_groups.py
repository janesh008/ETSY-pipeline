"""Script to automatically assign product_color and compatibility_groups to all lifestyle product surfaces."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIFESTYLE_PRODUCTS_DIR = PROJECT_ROOT / "etsy mockup creator" / "rendering" / "lifestyle_products"


COLOR_GROUP_MAP = {
    "white": ["dark_art", "colorful_art", "medium_art"],
    "cream": ["dark_art", "colorful_art", "medium_art"],
    "light_grey": ["dark_art", "colorful_art", "medium_art"],
    "beige": ["dark_art", "colorful_art", "medium_art"],
    "black": ["light_art", "colorful_art", "medium_art"],
    "dark_charcoal": ["light_art", "colorful_art", "medium_art"],
    "navy": ["light_art", "colorful_art", "medium_art"],
    "brown": ["dark_art", "medium_art"],
    "dark_brown": ["light_art", "medium_art"],
}


def infer_color_from_folder(folder_name: str) -> tuple[str, list[str]]:
    """Infer product_color and compatibility_groups from surface folder name."""
    name_lower = folder_name.lower()

    if "black" in name_lower or "charcoal" in name_lower:
        color = "black"
    elif "white" in name_lower:
        color = "white"
    elif "brown" in name_lower:
        color = "brown"
    elif "mug" in name_lower or "pillow" in name_lower or "wallart" in name_lower or "tshirt" in name_lower:
        color = "white"
    else:
        color = "white"

    groups = COLOR_GROUP_MAP.get(color, ["medium_art"])
    return color, groups


def assign_groups() -> int:
    """Scan all lifestyle product directories and write metadata.json with compatibility_groups."""
    if not LIFESTYLE_PRODUCTS_DIR.exists():
        print(f"[Error] Directory not found: {LIFESTYLE_PRODUCTS_DIR}")
        return 0

    updated_count = 0
    for entry in sorted(LIFESTYLE_PRODUCTS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        metadata_path = entry / "metadata.json"
        config_path = entry / "config.json"

        meta_dict = {}
        if metadata_path.exists():
            try:
                meta_dict = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[Warning] Failed to read {metadata_path}: {e}")

        # Read config.json for product_type or color if present
        config_dict = {}
        if config_path.exists():
            try:
                config_dict = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception as e:
                pass

        product_color = meta_dict.get("product_color") or config_dict.get("product_color")
        if not product_color:
            product_color, groups = infer_color_from_folder(entry.name)
        else:
            groups = COLOR_GROUP_MAP.get(product_color.lower(), ["medium_art"])

        meta_dict["template_name"] = meta_dict.get("template_name") or entry.name
        meta_dict["product_type"] = meta_dict.get("product_type") or config_dict.get("product_type", "tshirt")
        meta_dict["product_color"] = product_color
        meta_dict["compatibility_groups"] = meta_dict.get("compatibility_groups") or groups
        meta_dict["resolution"] = meta_dict.get("resolution") or config_dict.get("resolution", [4000, 4000])

        metadata_path.write_text(json.dumps(meta_dict, indent=2), encoding="utf-8")
        print(f"  [Updated] '{entry.name}' -> product_color='{product_color}', groups={meta_dict['compatibility_groups']}")
        updated_count += 1

    print(f"Successfully updated metadata for {updated_count} lifestyle product surfaces.")
    return updated_count


if __name__ == "__main__":
    assign_groups()
