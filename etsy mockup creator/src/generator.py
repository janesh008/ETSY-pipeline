import os
from typing import Dict, Any
from src.image_loader import ImageLoader
from src.template_loader import TemplateLoader
from src.renderer import Renderer

class Generator:
    """
    Orchestrates the entire batch mockup generation workflow.
    """
    @staticmethod
    def generate_all(theme_dir: str, templates_dir: str, output_dir: str):
        """
        Runs the mockup generator for all templates against a theme folder.
        """
        # Resolve theme name from folder name
        from pathlib import Path
        import re
        
        path_obj = Path(theme_dir)
        theme_folder_name = path_obj.name
        
        # If the selected folder is a known subfolder, use its parent name instead
        if theme_folder_name.lower() in ("processed_no_bg", "processed no bg", "processed-no-bg", "misc_category", "scen-pattern"):
            theme_folder_name = path_obj.parent.name
            
        clean_name = re.sub(r'[\s_\-]*\d+$', '', theme_folder_name)
        theme_name = clean_name.replace("_", " ")

        print(f"Starting Etsy Mockup Generation for Theme: '{theme_name}'")
        print(f"Loading images from: {theme_dir}")
        indexed_images = ImageLoader.load_theme_images(theme_dir)
        
        # Display index stats
        for cat, imgs in indexed_images.items():
            print(f"  - Category '{cat}': found {len(imgs)} images")
            
        if not indexed_images:
            raise ValueError(f"No categorized images found in '{theme_dir}'. Make sure images are in subfolders.")

        # Load templates
        print(f"Loading templates from: {templates_dir}")
        templates = TemplateLoader.load_all_templates(templates_dir)
        print(f"Loaded {len(templates)} templates.")

        # Ensure output folder exists
        os.makedirs(output_dir, exist_ok=True)

        # category_pointers track current sequential index for anti-duplication
        category_pointers = {}

        # Generate each mockup
        for template_file in os.listdir(templates_dir):
            if not template_file.lower().endswith(".json"):
                continue
                
            template_path = os.path.join(templates_dir, template_file)
            try:
                template = TemplateLoader.load_template(template_path)
            except Exception as e:
                print(f"Error loading template '{template_file}': {e}")
                continue

            template_name = template.get("name", "Mockup")
            output_filename = os.path.splitext(template_file)[0].capitalize() + ".png"
            output_path = os.path.join(output_dir, output_filename)
            
            # --- 2. Category Validation with Hero Fallback ---
            elements = template.get("elements", [])
            required_categories = set()
            for elem in elements:
                if elem.get("type") == "image" and elem.get("source"):
                    cat = elem.get("source", {}).get("category", "").lower()
                    if cat:
                        required_categories.add(cat)
            
            missing_categories = [cat for cat in required_categories if not indexed_images.get(cat)]

            if missing_categories:
                # Hero template gets special fallback treatment
                if template_file.lower() == "hero.json":
                    if not indexed_images.get("character"):
                        print(f"  [Skipped] Hero needs at least character images. Skipping.")
                        continue
                    # Renderer.render_template() handles filling missing slots with character images
                else:
                    print(f"  [Skipped] Template '{template_name}' requires categories {missing_categories} which are empty or missing. Skipping generation.")
                    continue

            print(f"Generating mockup '{template_name}' -> {output_filename}...")
            
            try:
                # Render using unique sequential category pointers
                canvas = Renderer.render_template(
                    template, 
                    theme_name, 
                    indexed_images, 
                    category_pointers=category_pointers,
                    template_name=template_file
                )
                canvas.save(output_path, "PNG")
                print(f"  [Success] Saved to {output_path}")
            except Exception as e:
                print(f"  [Failed] Error generating '{template_name}': {e}")
                import traceback
                traceback.print_exc()

        print("Mockup generation completed.")
        return True
