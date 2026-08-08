"""Script to run mockup generation using remote cloud assets from GCS (no_bg) and Google Drive (upscaled).

Fetches:
  1. no_bg transparent clipart PNGs from GCS bucket prefix:
     gs://<gcs_bucket>/Clipart/<date>/<theme_slug>/no_bg/
  2. 4K upscaled transparent clipart PNGs from Google Drive path:
     Clipart/main_data/<date>/<theme_slug>

Usage:
  python scripts/run_mockup_from_cloud.py --date 24062026 --theme baby_mickey
  python scripts/run_mockup_from_cloud.py --date 07082026 --theme Baby_Captain_America
  python scripts/run_mockup_from_cloud.py --list-remote
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

from etsy_pipeline.config.settings import get_settings
from etsy_pipeline.services.gcs_store import GCSStore, is_gcp_available
from etsy_pipeline.services.google_drive import GoogleDriveService
from rendering.plugins.orchestrator import RenderingOrchestrator


def format_date_candidates(date_str: str) -> list[str]:
    """Return date string candidates (e.g., '07082026' -> ['07082026', '2026-08-07'])."""
    candidates = [date_str]
    s = date_str.replace("-", "").replace("_", "").strip()
    if len(s) == 8 and s.isdigit():
        # DDMMYYYY -> YYYY-MM-DD
        day, month, year = s[:2], s[2:4], s[4:]
        iso_format = f"{year}-{month}-{day}"
        if iso_format not in candidates:
            candidates.append(iso_format)
        # YYYYMMDD -> YYYY-MM-DD
        iso_format_2 = f"{s[:4]}-{s[4:6]}-{s[6:]}"
        if iso_format_2 not in candidates:
            candidates.append(iso_format_2)
    return candidates


def download_gcs_no_bg_assets(
    gcs: GCSStore,
    date_folder: str,
    theme_slug: str,
    target_dir: Path,
) -> list[Path]:
    """Download no_bg transparent PNGs from GCS bucket prefix Clipart/<date>/<theme>/no_bg/."""
    date_candidates = format_date_candidates(date_folder)
    prefixes_to_try = []
    for d in date_candidates:
        prefixes_to_try.extend([
            f"Clipart/{d}/{theme_slug}/no_bg",
            f"Clipart/{d}/{theme_slug.lower()}/no_bg",
            f"Clipart/{d}/{theme_slug}",
            f"Clipart/{d}/{theme_slug.lower()}",
        ])

    png_objects = []
    matched_prefix = ""
    for gcs_prefix in prefixes_to_try:
        print(f"      Searching GCS prefix: gs://{gcs._bucket_name}/{gcs_prefix}/...")
        objects = gcs.list_objects(gcs_prefix)
        png_objects = [obj for obj in objects if obj.lower().endswith(".png")]
        if png_objects:
            matched_prefix = gcs_prefix
            print(f"      [Match] Found {len(png_objects)} PNG object(s) on GCS under '{gcs_prefix}'.")
            break

    if not png_objects:
        print(f"      [Warning] No PNG objects found on GCS bucket '{gcs._bucket_name}' for date '{date_folder}' & theme '{theme_slug}'.")
        return []

    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    clean_prefix = matched_prefix.rstrip("/") + "/"
    for obj_path in png_objects:
        fname = Path(obj_path).name
        dest_file = target_dir / fname
        if not dest_file.exists():
            gcs.download_file(obj_path, dest_file)
        downloaded.append(dest_file)

    print(f"      Successfully downloaded {len(downloaded)} no_bg PNG file(s) into {target_dir}")
    return downloaded


def download_drive_upscaled_assets(
    drive: GoogleDriveService,
    date_folder: str,
    theme_slug: str,
    target_dir: Path,
) -> list[Path]:
    """Download 4K upscaled PNGs from Google Drive path: Clipart/main_data/<date>/<theme>."""
    date_candidates = format_date_candidates(date_folder)
    paths_to_try = []
    for d in date_candidates:
        paths_to_try.extend([
            ["Clipart", "main_data", d, theme_slug],
            ["Clipart", "main_data", d, theme_slug.lower()],
            ["Clipart", "main_data", d, theme_slug, "upscaled"],
            ["Clipart", "raw_data", d, theme_slug, "no_bg"],
        ])

    folder_id = None
    matched_path = []
    for path_parts in paths_to_try:
        print(f"      Searching Google Drive path: {'/'.join(path_parts)}...")
        fid = drive.find_folder_id_by_path(
            parent_id=drive._settings.google_drive_folder_id,
            path_parts=path_parts,
        )
        if fid:
            folder_id = fid
            matched_path = path_parts
            break

    if not folder_id:
        print(f"      [Warning] No matching folder path found on Google Drive for date '{date_folder}' & theme '{theme_slug}'.")
        return []

    try:
        files = drive.list_files_in_folder(folder_id)
        png_files = [f for f in files if f.get("name", "").lower().endswith(".png")]

        if not png_files:
            print(f"      [Warning] No PNG files found in Drive folder '{'/'.join(matched_path)}'")
            return []

        print(f"      Found {len(png_files)} 4K upscaled file(s) on Google Drive. Downloading...")
        target_dir.mkdir(parents=True, exist_ok=True)

        downloaded: list[Path] = []
        for file_info in png_files:
            file_id = file_info["id"]
            fname = file_info["name"]
            dest_file = target_dir / fname
            if not dest_file.exists():
                drive.download_file(file_id, dest_file)
            downloaded.append(dest_file)

        print(f"      Successfully downloaded {len(downloaded)} 4K upscaled file(s) into {target_dir}")
        return downloaded
    except Exception as exc:
        print(f"      [Warning] Google Drive download failed: {exc}")
        return []


def list_remote_cloud_folders(settings):
    """List available date folders and themes on GCS and Drive for discovery."""
    print("\n--- Listing GCS Objects under 'Clipart/' ---")
    if is_gcp_available() or settings.gcs_bucket:
        try:
            gcs = GCSStore(settings=settings)
            objects = gcs.list_objects("Clipart/")
            print(f"GCS Bucket: {gcs._bucket_name}")
            date_folders = sorted(list({obj.split("/")[1] for obj in objects if len(obj.split("/")) > 1}))
            print(f"Available GCS Date Folders: {date_folders[:10]}")
            sample_themes = sorted(list({"/".join(obj.split("/")[:3]) for obj in objects if len(obj.split("/")) > 2}))
            print(f"Sample GCS Themes: {sample_themes[:15]}")
        except Exception as exc:
            print(f"[Error] GCS list failed: {exc}")

    print("\n--- Listing Google Drive folders under 'Clipart/main_data' ---")
    if settings.google_drive_folder_id:
        try:
            drive = GoogleDriveService(settings=settings)
            main_data_id = drive.find_folder_id_by_path(
                parent_id=settings.google_drive_folder_id,
                path_parts=["Clipart", "main_data"],
            )
            if main_data_id:
                subfolders = drive.list_files_in_folder(main_data_id)
                print(f"Available Drive Date Folders: {[f['name'] for f in subfolders]}")
        except Exception as exc:
            print(f"[Error] Drive list failed: {exc}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch GCS no_bg & Drive 4K upscaled assets for a theme date folder and run mockup generation."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date folder name on GCS/Drive (e.g., 07082026 or 24062026)",
    )
    parser.add_argument(
        "--theme",
        default=None,
        help="Theme slug name (e.g., Baby_Captain_America or baby_mickey)",
    )
    parser.add_argument(
        "--shop",
        default="all",
        help="Target shop ID ('all', 'pixelbarstudio', 'luna_cliparts', 'crisp_png_co')",
    )
    parser.add_argument(
        "--list-remote",
        action="store_true",
        help="List available date folders and themes on GCS and Drive",
    )
    parser.add_argument(
        "--theme-name",
        default=None,
        help="Optional human-readable theme display name for text overlays",
    )
    parser.add_argument(
        "--gcs-bucket",
        default=None,
        help="Optional GCS bucket override (e.g. etsy-pipeline-bucket)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory override",
    )
    parser.add_argument(
        "--nobg-dir",
        default=None,
        help="Optional local path to no_bg 700px assets (overrides GCS download)",
    )
    parser.add_argument(
        "--upscaled-dir",
        default=None,
        help="Optional local path to upscaled 4K assets (overrides Drive download)",
    )

    args = parser.parse_args()
    settings = get_settings()

    if args.gcs_bucket:
        settings.gcs_bucket = args.gcs_bucket

    if args.list_remote:
        list_remote_cloud_folders(settings)
        return

    if not args.date or not args.theme:
        print("[Error] Please specify --date and --theme, or use --list-remote to discover available folders.")
        return

    theme_slug = args.theme.strip()
    date_folder = args.date.strip()
    theme_display_name = args.theme_name or theme_slug.replace("_", " ").title()

    local_base_dir = PROJECT_ROOT / "output" / "cloud_assets" / date_folder / theme_slug
    no_bg_dir = Path(args.nobg_dir).resolve() if args.nobg_dir else (local_base_dir / "no_bg")
    upscaled_dir = Path(args.upscaled_dir).resolve() if args.upscaled_dir else (local_base_dir / "upscaled")

    output_root = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else PROJECT_ROOT / "output" / "cloud_mockup_runs" / date_folder / theme_slug
    )

    print("\n=======================================================")
    print("  CLOUD ASSET MOCKUP GENERATION RUNNER")
    print("=======================================================")
    print(f"  Date Folder:    {date_folder}")
    print(f"  Theme Slug:     {theme_slug}")
    print(f"  Theme Display:  {theme_display_name}")
    print(f"  Target Shop:    {args.shop}")
    print(f"  Local no_bg:    {no_bg_dir}")
    print(f"  Local upscaled: {upscaled_dir}")
    print(f"  Output Dir:     {output_root}")
    print("=======================================================\n")

    # Step 1: Download no_bg assets from GCS if not provided locally
    if args.nobg_dir and no_bg_dir.exists() and list(no_bg_dir.glob("*.png")):
        print(f"[1/2] Using provided local no_bg directory: {no_bg_dir}")
    else:
        print("[1/2] Syncing 'no_bg' transparent clipart assets from GCS...")
        if is_gcp_available() or settings.gcs_bucket:
            gcs_store = GCSStore(settings=settings)
            download_gcs_no_bg_assets(gcs_store, date_folder, theme_slug, no_bg_dir)
        else:
            print("      [Notice] GCP credentials / GCS bucket not configured locally. Skipping GCS download.")

    # Step 2: Download 4K upscaled assets from Google Drive main_data if not provided locally
    if args.upscaled_dir and upscaled_dir.exists() and list(upscaled_dir.glob("*.png")):
        print(f"[2/2] Using provided local upscaled directory: {upscaled_dir}")
    else:
        print("[2/2] Syncing '4K upscaled' transparent clipart assets from Google Drive...")
        if settings.google_drive_folder_id:
            try:
                drive_service = GoogleDriveService(settings=settings)
                download_drive_upscaled_assets(drive_service, date_folder, theme_slug, upscaled_dir)
            except Exception as exc:
                print(f"      [Warning] Google Drive download skipped: {exc}")
        else:
            print("      [Notice] GOOGLE_DRIVE_FOLDER_ID not set in .env. Skipping Drive download.")

    # Check local files count
    no_bg_count = len(list(no_bg_dir.glob("*.png"))) if no_bg_dir.exists() else 0
    upscaled_count = len(list(upscaled_dir.glob("*.png"))) if upscaled_dir.exists() else 0

    print(f"\n[Asset Check] Local no_bg images: {no_bg_count} | Local 4K upscaled images: {upscaled_count}")

    if no_bg_count == 0 and upscaled_count == 0:
        print("\n[Error] No assets available locally or downloaded from cloud. Please check date/theme name or run with --list-remote.")
        return

    # If no_bg is missing but upscaled exists, copy upscaled as fallback for no_bg
    if no_bg_count == 0 and upscaled_count > 0:
        print("      [Notice] no_bg folder is empty. Using upscaled images for standard canvas templates.")
        no_bg_dir = upscaled_dir

    # Determine shops to process
    rendering_root = MOCKUP_CREATOR_DIR / "rendering"
    orchestrator = RenderingOrchestrator(rendering_root)

    if args.shop.lower() == "all":
        shops = ["pixelbarstudio", "luna_cliparts", "crisp_png_co"]
    else:
        shops = [args.shop.strip()]

    total_generated = 0
    print("\n-------------------------------------------------------")
    print("  Dispatching Multi-Shop Rendering Pipeline...")
    print("-------------------------------------------------------")

    for shop_id in shops:
        shop_out_dir = output_root / shop_id
        print(f"\n--> [SHOP] Processing '{shop_id}'...")
        try:
            outputs = orchestrator.run(
                shop_id=shop_id,
                asset_dir=no_bg_dir,
                output_dir=shop_out_dir,
                theme_name=theme_display_name,
                upscaled_asset_dir=upscaled_dir if upscaled_count > 0 else None,
            )
            total_generated += len(outputs)
            print(f"    [Success] '{shop_id}' generated {len(outputs)} mockup file(s):")
            for p in outputs[:6]:
                size_mb = p.stat().st_size / 1024 / 1024 if p.exists() else 0
                print(f"      - {p.name} ({size_mb:.2f} MB)")
            if len(outputs) > 6:
                print(f"      ... and {len(outputs) - 6} more files")
        except Exception as exc:
            print(f"    [Error] Failed to render for shop '{shop_id}': {exc}")

    print("\n=======================================================")
    print(f"  Cloud Mockup Run Complete!")
    print(f"  Total Mockup Files Rendered: {total_generated}")
    print(f"  All outputs saved to: {output_root}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
