import os
from typing import Dict, List

class ImageLoader:
    """
    Scans a theme folder structure and indexes PNG images by category.
    Expected folder structure:
    Theme_Folder/
      category_name/
        image_001.png
        image_002.png
    """
    @staticmethod
    def load_theme_images(theme_dir: str) -> Dict[str, List[str]]:
        """
        Scans theme_dir for subdirectories (categories) and returns a dict mapping
        normalized category names to sorted lists of absolute PNG file paths.
        """
        if not os.path.isdir(theme_dir):
            raise FileNotFoundError(f"Theme directory '{theme_dir}' does not exist.")

        indexed_images: Dict[str, List[str]] = {}
        known_categories = [
            "subcharacter", "character", "combo", "prop", "pattern", "scene",
            "sub_character_1", "sub_character_2", "sub_character_3", "sub_character_4",
            "sub_character_5", "sub_character_6", "sub_character_7", "sub_character_8",
            "character_combo_2", "character_combo_3", "character_combo_4", "character_combo_full_group",
            "pattern_character", "pattern_object", "pattern_floral", "pattern_geometric",
            "prop_food", "prop_vehicle", "prop_weapon_tool", "prop_flower_nature", "prop_party",
            "scene_interior", "scene_exterior", "logo_emblem", "banner", "alphabet_number",
            "frame_border", "invitation_element"
        ]
        # Sort by length descending to match more specific names first (prevent e.g. "combo" matching inside "character_combo_2")
        known_categories = sorted(known_categories, key=len, reverse=True)
        
        for root, dirs, files in os.walk(theme_dir):
            for file in files:
                if file.lower().endswith(".png"):
                    full_path = os.path.abspath(os.path.join(root, file))
                    lower_name = file.lower()
                    
                    # Try to extract category from filename first
                    matched_category = None
                    for cat in known_categories:
                        if f"_{cat}_" in lower_name:
                            matched_category = cat
                            break
                    
                    # If not matched from filename, use subfolder name
                    if not matched_category:
                        # get parent folder name
                        parent_dir = os.path.basename(root)
                        matched_category = parent_dir.lower()
                        
                    if matched_category not in indexed_images:
                        indexed_images[matched_category] = []
                    indexed_images[matched_category].append(full_path)

        # Sort the image list for each category to ensure consistency
        for cat in indexed_images:
            indexed_images[cat].sort()

        # --- Build aggregate category pools for hero template compatibility ---
        # The hero template uses abstract names like "character", "combo", "prop"
        # but files use fine-grained names like "main_character", "character_combo_2", etc.
        # This step merges them into unified pools so the hero template can resolve images.
        AGGREGATE_MAP = {
            "character": [
                "main_character",
                "sub_character_1", "sub_character_2", "sub_character_3",
                "sub_character_4", "sub_character_5", "sub_character_6",
                "sub_character_7", "sub_character_8",
            ],
            "combo": [
                "character_combo_2", "character_combo_3",
                "character_combo_4", "character_combo_full_group",
            ],
        }

        for agg_name, source_cats in AGGREGATE_MAP.items():
            if agg_name not in indexed_images:  # don't overwrite if already exists
                pool = []
                for src in source_cats:
                    pool.extend(indexed_images.get(src, []))
                if pool:
                    indexed_images[agg_name] = sorted(pool)

        return indexed_images
