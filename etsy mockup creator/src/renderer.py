import os
import random
from typing import Any, Dict, List
from PIL import Image, ImageDraw
from src.effects import Effects
from src.text_renderer import TextRenderer

class Renderer:
    """
    Composites layers onto a canvas to create the final mockup image.
    """
    @staticmethod
    def create_gradient_background(width: int, height: int, start_color: str, end_color: str) -> Image.Image:
        """
        Creates a vertical linear gradient image.
        """
        # Parse hex colors
        def hex_to_rgb(hex_str: str):
            hex_str = hex_str.lstrip("#")
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
            
        try:
            c1 = hex_to_rgb(start_color)
            c2 = hex_to_rgb(end_color)
        except Exception:
            c1 = (240, 240, 240)
            c2 = (220, 220, 220)

        base = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base)
        
        for y in range(height):
            # Interpolate color
            r = int(c1[0] + (c2[0] - c1[0]) * (y / height))
            g = int(c1[1] + (c2[1] - c1[1]) * (y / height))
            b = int(c1[2] + (c2[2] - c1[2]) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
            
        return base

    @staticmethod
    def render_template(
        template: Dict[str, Any],
        theme_name: str,
        indexed_images: Dict[str, List[str]],
        assets_dir: str = "assets",
        category_pointers: Dict[str, int] = None,
        template_name: str = ""
    ) -> Image.Image:
        """
        Renders a mockup image according to the template schema.
        """
        canvas_size = template.get("canvas_size", [2000, 2000])
        w, h = canvas_size[0], canvas_size[1]
        
        # 1. Create base canvas
        bg_config = template.get("background", {})
        bg_type = bg_config.get("type", "color")
        
        if bg_type == "gradient":
            color_start = bg_config.get("color_start", "#FFFFFF")
            color_end = bg_config.get("color_end", "#CCCCCC")
            canvas = Renderer.create_gradient_background(w, h, color_start, color_end)
        elif bg_type == "image":
            image_path = bg_config.get("image_path")
            if image_path and os.path.exists(image_path):
                bg_img = Image.open(image_path).convert("RGBA")
                canvas = Effects.resize_fit(bg_img, w, h)
            else:
                # Fallback to white if background image is missing
                canvas = Image.new("RGBA", (w, h), "#FFFFFF")
        else:
            color = bg_config.get("color", "#FFFFFF")
            canvas = Image.new("RGBA", (w, h), color)

        # Draw context for overlays/text
        draw = ImageDraw.Draw(canvas)

        # Pre-calculate unique sequential image mapping for this template
        if category_pointers is None:
            category_pointers = {}
            
        elements = template.get("elements", [])
        template_mappings = {}
        for elem in elements:
            if elem.get("type") == "image" and elem.get("source"):
                source = elem.get("source", {})
                cat = source.get("category", "").lower()
                idx = source.get("index", 0)
                if cat not in template_mappings:
                    template_mappings[cat] = set()
                template_mappings[cat].add(idx)
                
        resolved_mappings = {}
        is_hero = template_name.lower().startswith("hero") or "hero" in template_name.lower()
        
        for cat, unique_indices in template_mappings.items():
            cat_images = indexed_images.get(cat, [])
            
            if not cat_images and is_hero:
                # Apply hero fallback: if combo/prop slot is empty, fill with character images
                cat_images = indexed_images.get("character", [])
                if cat_images:
                    print(f"  [Renderer Hero Fallback] Using 'character' pool for missing '{cat}' slots.")
                    
            if not cat_images:
                continue
            sorted_indices = sorted(list(unique_indices))
            
            if is_hero:
                # --- HERO MODE: Random selection from the FULL pool ---
                # Pick unique random images (no duplicates within this template)
                # Reset is intentional: hero should access ALL images, not just leftovers
                num_needed = len(sorted_indices)
                if num_needed <= len(cat_images):
                    selected = random.sample(cat_images, num_needed)
                else:
                    # More slots than images: pick all, then fill remaining randomly
                    selected = list(cat_images)
                    remaining = num_needed - len(cat_images)
                    selected.extend(random.choices(cat_images, k=remaining))
                
                for i, idx in enumerate(sorted_indices):
                    resolved_mappings[(cat, idx)] = selected[i]
                # Hero does NOT advance category_pointers (it's independent)
            else:
                # --- STANDARD MODE: Sequential pointer-based selection ---
                pointer = category_pointers.get(cat, 0)
                for i, idx in enumerate(sorted_indices):
                    resolved_mappings[(cat, idx)] = cat_images[(pointer + i) % len(cat_images)]
                category_pointers[cat] = (pointer + len(sorted_indices)) % len(cat_images)

        # 2. Render each element
        for element in elements:
            elem_type = element.get("type")
            
            if elem_type == "image":
                source = element.get("source", {})
                category = source.get("category", "").lower()
                index = source.get("index", 0)
                
                # Retrieve the image path using sequential mapping
                image_path = resolved_mappings.get((category, index))
                if not image_path:
                    category_images = indexed_images.get(category, [])
                    if not category_images:
                        print(f"Warning: No images found in category '{category}' for element. Skipping.")
                        continue
                    image_path = category_images[index % len(category_images)]
                
                try:
                    elem_img = Image.open(image_path).convert("RGBA")
                except Exception as e:
                    print(f"Error opening image '{image_path}': {e}")
                    continue
                
                # Apply scaling (keep aspect ratio inside target box)
                target_w = element.get("width", 500)
                target_h = element.get("height", 500)
                elem_img = Effects.resize_fit(elem_img, target_w, target_h)
                
                # Apply outline effect
                effects_cfg = element.get("effects", {})
                outline_cfg = effects_cfg.get("outline")
                if outline_cfg:
                    color_out = outline_cfg.get("color", "#FFFFFF")
                    width_out = outline_cfg.get("width", 5)
                    elem_img = Effects.apply_outline(elem_img, color_out, width_out)
                
                # Apply shadow effect
                shadow_cfg = effects_cfg.get("shadow")
                if shadow_cfg:
                    color_sh = shadow_cfg.get("color", "#00000040")
                    offset_sh = tuple(shadow_cfg.get("offset", [10, 10]))
                    blur_sh = shadow_cfg.get("blur", 10)
                    elem_img = Effects.apply_shadow(elem_img, color_sh, offset_sh, blur_sh)
                
                # Apply rotation
                rotation = element.get("rotation", 0)
                if rotation != 0:
                    elem_img = Effects.rotate_image(elem_img, rotation)
                
                # Composite position
                x = element.get("x", w // 2)
                y = element.get("y", h // 2)
                anchor = element.get("anchor", "center")
                
                elem_w, elem_h = elem_img.size
                if anchor == "center" or anchor == "middle":
                    paste_x = int(x - elem_w / 2)
                    paste_y = int(y - elem_h / 2)
                else: # top-left default
                    paste_x = int(x)
                    paste_y = int(y)
                
                # Paste transparent image onto canvas
                canvas.paste(elem_img, (paste_x, paste_y), elem_img)

            elif elem_type == "text":
                content = element.get("content", "")
                
                # Calculate bundle count (unique images only, skipping duplicates from aggregate pools)
                unique_images = set()
                for imgs in indexed_images.values():
                    unique_images.update(imgs)
                bundle_count = str(len(unique_images))
                
                # Variable interpolation
                content = content.replace("{theme_name_title}", theme_name.title())
                content = content.replace("{theme_name_upper}", theme_name.upper())
                content = content.replace("{theme_name}", theme_name)
                content = content.replace("{bundle_count}", bundle_count)
                
                x = element.get("x", w // 2)
                y = element.get("y", h // 2)
                font_family = element.get("font_family", "Outfit-Regular")
                font_size = element.get("font_size", 48)
                color = element.get("color", "#000000")
                anchor = element.get("anchor", "center")
                align = element.get("align", "center")
                max_width = element.get("max_width", 0)
                
                TextRenderer.render_text(
                    draw=draw,
                    text=content,
                    position=(x, y),
                    font_path=font_family,
                    font_size=font_size,
                    color=color,
                    anchor=anchor,
                    align=align,
                    max_width=max_width
                )

        return canvas
