import os
from PIL import ImageFont, ImageDraw, Image

class TextRenderer:
    """
    Renders text onto PIL canvases with support for custom fonts, wrapping, colors, and anchors.
    """
    @staticmethod
    def resolve_font(font_path_or_name: str, size: int) -> ImageFont.ImageFont:
        """
        Attempts to load a font from a path, standard OS directories, or falls back to default.
        """
        try:
            # 1. Try direct path
            if os.path.exists(font_path_or_name):
                return ImageFont.truetype(font_path_or_name, size)
            
            # 2. Try with .ttf extension directly
            if not font_path_or_name.lower().endswith(('.ttf', '.otf')):
                direct_ttf = font_path_or_name + ".ttf"
                if os.path.exists(direct_ttf):
                    return ImageFont.truetype(direct_ttf, size)
            
            # 3. Try searching in assets/fonts/
            fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
            if os.path.exists(fonts_dir):
                # Try raw name
                assets_path = os.path.join(fonts_dir, font_path_or_name)
                if os.path.exists(assets_path):
                    return ImageFont.truetype(assets_path, size)
                
                # Try with .ttf suffix
                assets_ttf = assets_path + ".ttf"
                if os.path.exists(assets_ttf):
                    return ImageFont.truetype(assets_ttf, size)
                
                # Try normalized search (case-insensitive, stripping spaces and hyphens)
                font_clean = font_path_or_name.replace(" ", "").replace("-", "").lower()
                for filename in os.listdir(fonts_dir):
                    file_name_only = os.path.splitext(filename)[0]
                    file_clean = file_name_only.replace(" ", "").replace("-", "").lower()
                    if file_clean == font_clean or file_clean == font_clean + "regular" or file_clean == font_clean + "bold":
                        return ImageFont.truetype(os.path.join(fonts_dir, filename), size)
            
            # 4. Try default system directories via Pillow's native lookup
            try:
                return ImageFont.truetype(font_path_or_name, size)
            except Exception:
                pass
                
            if not font_path_or_name.lower().endswith(('.ttf', '.otf')):
                try:
                    return ImageFont.truetype(font_path_or_name + ".ttf", size)
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"Warning error loading font '{font_path_or_name}': {e}")
            
        # Fall back to default system font
        print(f"Warning: Could not resolve font '{font_path_or_name}'. Falling back to default system font.")
        try:
            return ImageFont.load_default()
        except Exception:
            return None

    @staticmethod
    def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        """
        Wraps text to fit within a maximum width based on the font size.
        """
        if not font or max_width <= 0:
            return text
            
        words = text.split(" ")
        lines = []
        current_line = []
        
        for word in words:
            # Test putting word in current line
            test_line = " ".join(current_line + [word])
            # In Pillow 10, use font.getlength or getbbox
            try:
                bbox = font.getbbox(test_line)
                line_width = bbox[2] - bbox[0]
            except Exception:
                # Fallback for older PIL
                line_width = font.getsize(test_line)[0]
                
            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                
        if current_line:
            lines.append(" ".join(current_line))
            
        return "\n".join(lines)

    @staticmethod
    def render_text(
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple,
        font_path: str,
        font_size: int,
        color: str,
        anchor: str = "la",  # PIL text anchors: e.g. "mm" for middle-middle, "la" for left-ascender
        align: str = "left",
        max_width: int = 0
    ):
        """
        Renders multi-line text onto the drawing context.
        """
        font = TextRenderer.resolve_font(font_path, font_size)
        
        if max_width > 0:
            text = TextRenderer.wrap_text(text, font, max_width)
            
        # Draw multiline text
        # If anchor is 'center' or 'middle', we map to PIL anchor 'mm' (middle horizontal, middle vertical) or similar.
        # Standardize anchor name conversions.
        pil_anchor = anchor
        if anchor == "center" or anchor == "middle":
            pil_anchor = "ms"  # middle-baseline, or mm
        elif anchor == "top-left":
            pil_anchor = "la"
        elif anchor == "top-center":
            pil_anchor = "ma"
            
        draw.multiline_text(
            position,
            text,
            fill=color,
            font=font,
            anchor=pil_anchor,
            align=align,
            spacing=10
        )

