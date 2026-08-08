import os

from src.image_loader import ImageLoader
from src.renderer import Renderer
from src.template_loader import TemplateLoader


class Generator:
    """
    Orchestrates the entire batch mockup generation workflow.
    """
    @staticmethod
    def generate_all(
        theme_dir: str,
        templates_dir: str,
        output_dir: str,
        theme_name: str | None = None,
        template_override: str | None = None,
    ):
        """Runs the mockup generator with visual compatibility template selection."""
        import re
        from pathlib import Path
        from rendering.compatibility.clipart_analyzer import ClipartAnalyzer
        from rendering.compatibility.compatibility_engine import CompatibilityEngine

        if theme_name and theme_name.strip():
            theme_folder_name = theme_name.strip()
        else:
            path_obj = Path(theme_dir)
            theme_folder_name = path_obj.name

            if theme_folder_name.lower() in (
                "no_bg", "no bg", "no-bg", "nobg",
                "processed_no_bg", "processed no bg", "processed-no-bg",
                "misc_category", "scen-pattern"
            ):
                theme_folder_name = path_obj.parent.name

        clean_name = re.sub(r'[\s_\-]*\d+$', '', theme_folder_name)
        theme_name = clean_name.replace("_", " ")

        print(f"Starting Etsy Mockup Generation for Theme: '{theme_name}'")
        print(f"Loading images from: {theme_dir}")
        indexed_images = ImageLoader.load_theme_images(theme_dir)

        for cat, imgs in indexed_images.items():
            print(f"  - Category '{cat}': found {len(imgs)} images")

        if not indexed_images:
            raise ValueError(f"No categorized images found in '{theme_dir}'. Make sure images are in subfolders.")

        # --- Visual Clipart Compatibility Analysis ---
        sample_clipart_path = None
        for cat_list in ("character", "main_character", "scene", "prop"):
            if indexed_images.get(cat_list):
                sample_clipart_path = indexed_images[cat_list][0]
                break
        if not sample_clipart_path:
            for imgs in indexed_images.values():
                if imgs:
                    sample_clipart_path = imgs[0]
                    break

        print(f"[Compatibility] Analyzing sample clipart: {sample_clipart_path}")
        analysis = ClipartAnalyzer.analyze_clipart(sample_clipart_path)
        print(f"  - Clipart Brightness: {analysis.brightness_category} ({analysis.average_brightness:.2f})")
        print(f"  - Clipart Saturation: {analysis.saturation_category} ({analysis.saturation:.2f})")
        print(f"  - Dominant Colors: {analysis.dominant_colors[:3]}")

        # Load templates
        print(f"Loading templates from: {templates_dir}")
        loaded_template_tuples = []
        for template_file in os.listdir(templates_dir):
            if not template_file.lower().endswith(".json"):
                continue
            t_path = os.path.join(templates_dir, template_file)
            try:
                t_dict = TemplateLoader.load_template(t_path)
                loaded_template_tuples.append((template_file, t_dict))
            except Exception as e:
                print(f"Error loading template '{template_file}': {e}")
                continue

        if not loaded_template_tuples:
            raise ValueError(f"No valid template JSON files loaded from '{templates_dir}'.")

        # Rank templates using CompatibilityEngine
        selection_result = CompatibilityEngine.rank_templates(
            analysis=analysis,
            templates=loaded_template_tuples,
            min_score_threshold=0.50,
            override_template_id=template_override,
        )

        print(
            f"[CompatibilitySelection] Selected Optimal Template: '{selection_result.selected_template_id}' "
            f"(Score: {selection_result.score:.3f})"
        )

        os.makedirs(output_dir, exist_ok=True)
        category_pointers = {}

        # Render selected template and compatible templates
        for template_file, template in loaded_template_tuples:
            template_name = template.get("name", "Mockup")
            output_filename = os.path.splitext(template_file)[0].capitalize() + ".png"
            output_path = os.path.join(output_dir, output_filename)

            elements = template.get("elements", [])
            required_categories = set()
            for elem in elements:
                if elem.get("type") == "image" and elem.get("source"):
                    cat = elem.get("source", {}).get("category", "").lower()
                    if cat:
                        required_categories.add(cat)

            missing_categories = [cat for cat in required_categories if not indexed_images.get(cat)]

            if missing_categories:
                if template_file.lower() == "hero.json":
                    if not indexed_images.get("character"):
                        print("  [Skipped] Hero needs at least character images. Skipping.")
                        continue
                else:
                    print(f"  [Skipped] Template '{template_name}' requires categories {missing_categories}. Skipping.")
                    continue

            print(f"Generating mockup '{template_name}' -> {output_filename}...")

            try:
                canvas = Renderer.render_template(
                    template,
                    theme_name,
                    indexed_images,
                    category_pointers=category_pointers,
                    template_name=template_file
                )
                # Save PNG
                canvas.save(output_path, "PNG")

                # Save high-quality optimized JPEG (Quality 93) for fast Etsy API upload (~800KB - 1.2MB)
                jpg_filename = os.path.splitext(template_file)[0].capitalize() + ".jpg"
                jpg_path = os.path.join(output_dir, jpg_filename)
                rgb_canvas = canvas.convert("RGB")
                rgb_canvas.save(jpg_path, "JPEG", quality=93, optimize=True)

                print(f"  [Success] Saved to {output_path} and {jpg_path}")
            except Exception as e:
                print(f"  [Failed] Error generating '{template_name}': {e}")
                import traceback
                traceback.print_exc()

        print("Mockup generation completed.")
        return True
