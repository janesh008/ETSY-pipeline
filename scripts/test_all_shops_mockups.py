"""Test Script to run full mockup rendering across ALL 3 SHOPS (Shop 1, Shop 2, Shop 3).

Demonstrates:
  - Shop 1 (pixelbarstudio): Standard Hero canvas mockups (using no_bg 700px).
  - Shop 2 (luna_cliparts): Standard Hero canvas mockups + Smart Lifestyle photos (using 4K upscaled).
  - Shop 3 (crisp_png_co): Standard Hero canvas mockups (using no_bg 700px).

Usage:
  python scripts/test_all_shops_mockups.py
  python scripts/test_all_shops_mockups.py --nobg-dir "path/to/no_bg" --upscaled-dir "path/to/upscaled"
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

from rendering.plugins.orchestrator import RenderingOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Run end-to-end multi-shop mockup rendering test across Shop 1, Shop 2, and Shop 3."
    )
    parser.add_argument(
        "--nobg-dir",
        default=str(MOCKUP_CREATOR_DIR / "tests" / "sample_theme"),
        help="Path to folder containing 700px no_bg transparent PNGs",
    )
    parser.add_argument(
        "--upscaled-dir",
        default=r"D:\Janesh\ETSY\CrispPNGCo\24062026-pending\baby_mickey\upscaled",
        help="Path to folder containing 4K upscaled transparent PNGs",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "output" / "all_shops_test_output"),
        help="Root output folder for generated mockups",
    )
    parser.add_argument(
        "--theme-name",
        default="Baby Mickey",
        help="Display theme name for text interpolation",
    )

    args = parser.parse_args()

    nobg_dir = Path(args.nobg_dir).resolve()
    upscaled_dir = Path(args.upscaled_dir).resolve()
    output_root = Path(args.output_root).resolve()
    rendering_root = MOCKUP_CREATOR_DIR / "rendering"

    print("=======================================================")
    print("  ALL SHOPS END-TO-END MOCKUP TEST RUNNER")
    print("=======================================================")
    print(f"  Standard Assets (no_bg):   {nobg_dir}")
    print(f"  4K Upscaled Assets:        {upscaled_dir}")
    print(f"  Output Root Directory:     {output_root}")
    print(f"  Theme Display Name:        {args.theme_name}")
    print("=======================================================\n")

    orchestrator = RenderingOrchestrator(rendering_root)
    shops_to_test = ["pixelbarstudio", "luna_cliparts", "crisp_png_co"]

    total_generated = 0
    for shop_id in shops_to_test:
        shop_out_dir = output_root / shop_id
        print(f"--> [SHOP] Processing '{shop_id}'...")
        try:
            outputs = orchestrator.run(
                shop_id=shop_id,
                asset_dir=nobg_dir,
                output_dir=shop_out_dir,
                theme_name=args.theme_name,
                upscaled_asset_dir=upscaled_dir,
            )
            total_generated += len(outputs)
            print(f"    [Success] '{shop_id}' generated {len(outputs)} mockup file(s):")
            for p in outputs[:4]:
                size_mb = p.stat().st_size / 1024 / 1024 if p.exists() else 0
                print(f"      - {p.name} ({size_mb:.2f} MB)")
            if len(outputs) > 4:
                print(f"      ... and {len(outputs) - 4} more files")
        except Exception as exc:
            print(f"    [Error] Failed to render for shop '{shop_id}': {exc}")

    print("\n=======================================================")
    print(f"  Test Complete! Total Mockups Rendered: {total_generated}")
    print(f"  Results saved to: {output_root}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
