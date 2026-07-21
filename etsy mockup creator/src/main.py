import os
import argparse
import urllib.request
from src.generator import Generator

FONT_URLS = {
    "Outfit-Bold.ttf": "https://github.com/AsteroidOS/asteroid-fonts/raw/master/Outfit-Bold.ttf",
    "Outfit-Regular.ttf": "https://github.com/AsteroidOS/asteroid-fonts/raw/master/Outfit-Regular.ttf"
}

def ensure_assets():
    """
    Downloads free Google Fonts if they don't exist in assets/fonts.
    """
    fonts_dir = os.path.join("assets", "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    
    for font_name, url in FONT_URLS.items():
        font_path = os.path.join(fonts_dir, font_name)
        if not os.path.exists(font_path):
            print(f"Font '{font_name}' not found. Downloading from Google Fonts...")
            try:
                # Set headers to look like a browser request to prevent blockings
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req) as response, open(font_path, "wb") as out_file:
                    out_file.write(response.read())
                print(f"Successfully downloaded {font_name} to {font_path}")
            except Exception as e:
                print(f"Failed to download font {font_name}: {e}. System font fallback will be used.")

def main():
    parser = argparse.ArgumentParser(description="Automated Etsy Mockup Generator")
    parser.add_argument(
        "--theme",
        type=str,
        help="Path to the theme folder containing categorized PNG images (required if not using --batch-dir)"
    )
    parser.add_argument(
        "--templates",
        type=str,
        default="templates",
        help="Path to the templates folder containing JSON mockup specifications (default: templates)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to the output folder where PNG mockups will be generated (required if not using --batch-dir)"
    )
    parser.add_argument(
        "--batch-dir",
        type=str,
        help="Path to the main directory containing multiple theme folders to process in a single batch run"
    )
    
    args = parser.parse_args()
    
    # Pre-checks & asset acquisition
    ensure_assets()
    
    if not args.batch_dir and (not args.theme or not args.output):
        parser.error("Either --batch-dir OR both --theme and --output must be provided.")
        
    try:
        if args.batch_dir:
            batch_path = os.path.abspath(args.batch_dir)
            if not os.path.exists(batch_path) or not os.path.isdir(batch_path):
                print(f"Error: Batch directory does not exist or is not a folder: {batch_path}")
                return
                
            print(f"Starting batch generation inside main directory: {batch_path}")
            theme_dirs = []
            for entry in os.scandir(batch_path):
                if entry.is_dir() and not entry.name.startswith("."):
                    # Check if it has any PNG files recursively
                    has_png = False
                    for root, dirs, files in os.walk(entry.path):
                        if any(f.lower().endswith(".png") for f in files):
                            has_png = True
                            break
                    if has_png:
                        theme_dirs.append(entry)
                        
            if not theme_dirs:
                print("No valid theme subdirectories found inside the batch folder.")
                return
                
            print(f"Found {len(theme_dirs)} theme folders to process:")
            for t in theme_dirs:
                print(f"  - {t.name}")
                
            success_count = 0
            for t in theme_dirs:
                theme_path = t.path
                output_path = os.path.join(theme_path, "etsy_mockups")
                print(f"\n=========================================")
                print(f"Processing Theme: '{t.name}'")
                print(f"=========================================")
                try:
                    Generator.generate_all(
                        theme_dir=theme_path,
                        templates_dir=args.templates,
                        output_dir=output_path
                    )
                    success_count += 1
                except Exception as e:
                    print(f"Failed to process theme '{t.name}': {e}")
                    
            print(f"\nBatch processing complete. Successfully processed {success_count}/{len(theme_dirs)} themes.")
        else:
            Generator.generate_all(
                theme_dir=args.theme,
                templates_dir=args.templates,
                output_dir=args.output
            )
    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    main()
