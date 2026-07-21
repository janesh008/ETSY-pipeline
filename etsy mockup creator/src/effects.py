from PIL import Image, ImageFilter, ImageOps
import math

class Effects:
    """
    Applies visual effects to Pillow Images: resizing, rotation, outlines, and drop shadows.
    """
    @staticmethod
    def resize_fit(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """
        Resizes an image to fit within the specified bounding box while maintaining aspect ratio.
        """
        # Original dimensions
        orig_w, orig_h = image.size
        
        # Calculate ratio
        ratio = min(max_width / orig_w, max_height / orig_h)
        new_w = max(1, int(orig_w * ratio))
        new_h = max(1, int(orig_h * ratio))
        
        return image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    @staticmethod
    def rotate_image(image: Image.Image, angle: float) -> Image.Image:
        """
        Rotates the image by the specified angle (in degrees, counter-clockwise)
        expanding the canvas to fit the rotated image without clipping.
        """
        if angle == 0:
            return image
        return image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    @staticmethod
    def apply_outline(image: Image.Image, color: str, width: int) -> Image.Image:
        """
        Applies a clean border/outline around the transparent elements of a PNG.
        Uses MaxFilter on the alpha channel to dilate it.
        """
        if width <= 0:
            return image
            
        # Ensure image has alpha channel
        img = image.convert("RGBA")
        alpha = img.getchannel("A")
        
        # Dilate alpha channel using MaxFilter
        # MaxFilter(size) requires odd integer.
        filter_size = width * 2 + 1
        dilated_alpha = alpha.filter(ImageFilter.MaxFilter(filter_size))
        
        # Create solid color background
        outline_bg = Image.new("RGBA", img.size, color)
        # Apply the dilated alpha mask to the color background
        outline_bg.putalpha(dilated_alpha)
        
        # Composite original image over the outline background
        composite = Image.alpha_composite(outline_bg, img)
        return composite

    @staticmethod
    def apply_shadow(image: Image.Image, color: str, offset: tuple, blur_radius: int) -> Image.Image:
        """
        Creates a drop shadow behind the transparent elements of a PNG.
        """
        if blur_radius <= 0 and offset == (0, 0):
            return image

        img = image.convert("RGBA")
        w, h = img.size
        dx, dy = offset

        # Pad canvas to accommodate offset and blur without clipping the shadow
        pad_x = abs(dx) + blur_radius * 2
        pad_y = abs(dy) + blur_radius * 2

        padded_w = w + pad_x * 2
        padded_h = h + pad_y * 2

        # Create target container image
        shadow_canvas = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
        
        # Extract alpha channel
        alpha = img.getchannel("A")
        
        # Create shadow mask
        shadow_mask = Image.new("RGBA", (w, h), color)
        shadow_mask.putalpha(alpha)
        
        # Paste shadow with offset
        shadow_x = pad_x + dx
        shadow_y = pad_y + dy
        shadow_canvas.paste(shadow_mask, (shadow_x, shadow_y), shadow_mask)
        
        # Blur the shadow
        if blur_radius > 0:
            shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(blur_radius))
            
        # Paste original image onto the padded canvas (un-offset)
        original_x = pad_x
        original_y = pad_y
        original_img_padded = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
        original_img_padded.paste(img, (original_x, original_y), img)
        
        # Composite them
        result = Image.alpha_composite(shadow_canvas, original_img_padded)
        
        # Crop the transparent borders slightly if they are excessively large,
        # but keep it simple and just return the result.
        return result
