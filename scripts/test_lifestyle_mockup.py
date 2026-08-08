"""Test script for testing multi-shop lifestyle mockup rendering on custom clipart PNGs.

Usage:
    python scripts/test_lifestyle_mockup.py
    python scripts/test_lifestyle_mockup.py --shop luna_cliparts --product tshirt --clipart-dir path/to/your/pngs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project roots to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCKUP_CREATOR_DIR = PROJECT_ROOT / "etsy mockup creator"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MOCKUP_CREATOR_DIR))

from rendering.plugins.lifestyle_plugin import LifestylePlugin
from rendering.plugins.orchestrator import RenderingOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Test multi-shop lifestyle mockup creation on custom clipart assets."
    )
    parser.add_argument(
        "--shop",
        default="luna_cliparts",
        help="Shop ID (e.g., luna_cliparts, crisp_png_co, pixelbarstudio)",
    )
    parser.add_argument(
        "--product",
        default="tshirt",
        help="Product template name (e.g., tshirt, mug, frame)",
    )
    parser.add_argument(
        "--clipart-dir",
        default=str(PROJECT_ROOT / "output" ),
        help="Path to folder containing clipart transparent PNG files",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "output" / "test_lifestyle_output"),
        help="Where to save the rendered output mockups",
    )
    parser.add_argument(
        "--theme-name",
        default="Test Clipart Theme",
        help="Theme display name for rendering text overlays",
    )

    args = parser.parse_args()

    clipart_dir = Path(args.clipart_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    rendering_root = MOCKUP_CREATOR_DIR / "rendering"
    template_dir = rendering_root / "lifestyle_products" / args.product

    print(f"\n=======================================================")
    print(f"  Multi-Shop Lifestyle Mockup Test Runner")
    print(f"=======================================================")
    print(f"  Shop ID:        {args.shop}")
    print(f"  Product:        {args.product}")
    print(f"  Clipart Dir:    {clipart_dir}")
    print(f"  Template Dir:   {template_dir}")
    print(f"  Output Dir:     {output_dir}")
    print(f"=======================================================\n")

    if not clipart_dir.exists():
        print(f"ERROR: Clipart directory does not exist: {clipart_dir}")
        sys.exit(1)

    png_files = list(clipart_dir.rglob("*.png"))
    print(f"Found {len(png_files)} PNG files in clipart directory.")

    if not template_dir.exists():
        print(f"ERROR: Template directory does not exist: {template_dir}")
        sys.exit(1)

    plugin = LifestylePlugin()
    try:
        results = plugin.render(
            asset_dir=clipart_dir,
            output_dir=output_dir,
            template_dir=template_dir,
            theme_name=args.theme_name,
            shop_id=args.shop,
        )
        print(f"\n[SUCCESS] Rendered {len(results)} mockup image(s):")
        for res in results:
            print(f"   -> {res.resolve()}")
    except Exception as exc:
        print(f"\n[FAILED] {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
