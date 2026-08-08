"""LifestylePlugin — Pillow + OpenCV product mockup compositor.

Overlays transparent PNG collages onto professional blank product photos
using mask compositing, perspective warping, and fabric shadow blending.
Preserves full RGBA alpha transparency throughout the entire pipeline.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops

from etsy_pipeline.utils.exceptions import RenderingPluginError
from etsy_pipeline.utils.logging import get_logger
from rendering.plugins.base_plugin import BasePlugin

try:
    import cv2

    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

logger = get_logger(__name__)


class LifestylePlugin(BasePlugin):
    """Generates realistic lifestyle product mockups with strict RGBA alpha preservation.

    Pipeline:
        1. Load RGBA artwork / build collage (preserve alpha).
        2. Fit / perspective-warp artwork onto target print area (preserve alpha).
        3. Apply mask.png as a clipping mask ONLY to the alpha channel.
        4. Apply shadow_overlay.png fabric shading ONLY to the print layer RGB.
        5. Composite shaded print layer onto blank shirt photo using alpha_composite.
    """

    def render(
        self,
        asset_dir: Path,
        output_dir: Path,
        template_dir: Path,
        theme_name: str,
        shop_id: str,
        debug: bool = True,
    ) -> list[Path]:
        """Render lifestyle product mockup for a theme asset folder.

        Args:
            asset_dir: Path to no_bg/ transparent PNGs.
            output_dir: Output directory for rendered mockups.
            template_dir: Path to product template directory.
            theme_name: Display name of the active theme.
            shop_id: Shop identifier.
            debug: If True, writes intermediate debug PNG files (01..05).

        Returns:
            List of generated output image file paths.

        Raises:
            RenderingPluginError: If config parsing or rendering fails fatally.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        config_path = template_dir / "config.json"
        if not config_path.exists():
            logger.warning(
                f"[LifestylePlugin:{shop_id}] Config missing at {config_path}. Skipping product."
            )
            return []

        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            error_msg = f"Failed to parse lifestyle config JSON at {config_path}: {exc}"
            logger.error(f"[LifestylePlugin:{shop_id}] {error_msg}")
            raise RenderingPluginError("LifestylePlugin", error_msg) from exc

        blank_path = template_dir / "blank.png"
        mask_path = template_dir / "mask.png"
        shadow_path = template_dir / "shadow_overlay.png"

        # Determine canvas resolution (accept canvas_size or resolution)
        res = config.get("canvas_size") or config.get("resolution") or [3000, 3000]
        canvas_w, canvas_h = int(res[0]), int(res[1])

        # Load blank photo
        if blank_path.exists():
            try:
                blank_img = Image.open(blank_path).convert("RGBA")
                if blank_img.size != (canvas_w, canvas_h):
                    blank_img = blank_img.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            except Exception as exc:
                error_msg = f"Failed to open blank.png at {blank_path}: {exc}"
                logger.error(f"[LifestylePlugin:{shop_id}] {error_msg}")
                raise RenderingPluginError("LifestylePlugin", error_msg) from exc
        else:
            logger.info(
                f"[LifestylePlugin:{shop_id}] Note: blank.png not found in {template_dir.name}. "
                "Using fallback neutral composite canvas."
            )
            blank_img = Image.new("RGBA", (canvas_w, canvas_h), (245, 245, 247, 255))

        # Collect PNG assets
        png_files = sorted(list(asset_dir.rglob("*.png")))
        if not png_files:
            logger.warning(
                f"[LifestylePlugin:{shop_id}] No PNG assets found in {asset_dir}. Skipping."
            )
            return []

        # ---------------------------------------------------------------------
        # STEP 1: Load/Build Artwork RGBA
        # ---------------------------------------------------------------------
        max_imgs = config.get("asset_selection", {}).get("max_images", 16)
        selected_assets = png_files[:max_imgs]
        artwork_rgba = self._build_collage(selected_assets, target_size=(2000, 2000))

        self._log_artwork_stats("01_artwork_rgba", artwork_rgba)
        if debug:
            artwork_rgba.save(output_dir / "01_artwork_rgba.png")

        # ---------------------------------------------------------------------
        # STEP 2: Perspective Transform
        # ---------------------------------------------------------------------
        print_area = config.get("print_area", {})
        corners = self._parse_corners(print_area, (canvas_w, canvas_h))

        perspective_artwork = self._warp_perspective_rgba(
            artwork_rgba, corners, (canvas_w, canvas_h)
        )

        self._log_artwork_stats("02_perspective_artwork", perspective_artwork)
        if debug:
            perspective_artwork.save(output_dir / "02_perspective_artwork.png")

        # ---------------------------------------------------------------------
        # STEP 3: Apply Mask as Clipping Mask ONLY
        # ---------------------------------------------------------------------
        masked_artwork = perspective_artwork.copy()

        if mask_path.exists():
            try:
                mask_img = Image.open(mask_path).convert("L")
                if mask_img.size != (canvas_w, canvas_h):
                    mask_img = mask_img.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)

                # Log mask stats
                mask_arr = np.array(mask_img)
                white_pct = (np.sum(mask_arr > 128) / mask_arr.size) * 100.0
                logger.info(
                    f"[LifestylePlugin] Mask dimensions: {mask_img.size}, White area: {white_pct:.2f}%"
                )

                # Multiply alpha channel by mask_img to clip artwork outside printable region
                r, g, b, a = masked_artwork.split()
                clipped_a = ImageChops.multiply(a, mask_img)
                masked_artwork = Image.merge("RGBA", (r, g, b, clipped_a))
            except Exception as exc:
                logger.warning(
                    f"[LifestylePlugin:{shop_id}] Could not apply mask from {mask_path}: {exc}"
                )

        self._log_artwork_stats("03_masked_artwork", masked_artwork)
        if debug:
            masked_artwork.save(output_dir / "03_masked_artwork.png")

        # ---------------------------------------------------------------------
        # STEP 4: Apply Fabric Shading to Print Layer ONLY
        # ---------------------------------------------------------------------
        shadow_applied_artwork = masked_artwork.copy()

        if shadow_path.exists():
            try:
                shadow_img = Image.open(shadow_path).convert("RGBA")
                if shadow_img.size != (canvas_w, canvas_h):
                    shadow_img = shadow_img.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)

                opacity = float(
                    config.get("default_shadow")
                    or config.get("compositing", {}).get("shadow_opacity", 0.75)
                )

                # Extract RGB channels of artwork and shadow
                art_r, art_g, art_b, art_a = shadow_applied_artwork.split()
                art_rgb = Image.merge("RGB", (art_r, art_g, art_b))

                shd_r, shd_g, shd_b, _ = shadow_img.split()
                shd_rgb = Image.merge("RGB", (shd_r, shd_g, shd_b))

                # Normalize shadow overlay so highest luminance in print area is 255
                # This ensures artwork colors stay vibrant while inheriting wrinkles/shading
                shd_arr = np.array(shd_rgb, dtype=np.float32)
                mask_np = np.array(mask_img) > 128 if mask_path.exists() else np.ones(shd_arr.shape[:2], dtype=bool)
                if np.any(mask_np):
                    max_val = np.percentile(shd_arr[mask_np], 98)
                    if max_val > 10:
                        shd_arr = np.clip(shd_arr * (255.0 / max_val), 0, 255)
                shd_norm_rgb = Image.fromarray(shd_arr.astype(np.uint8), "RGB")

                # Multiply artwork RGB by normalized shadow overlay RGB
                multiplied_rgb = ImageChops.multiply(art_rgb, shd_norm_rgb)

                # Blend multiplied RGB with original artwork RGB by shadow opacity
                shaded_rgb = Image.blend(art_rgb, multiplied_rgb, opacity)

                # Re-assemble RGBA with the masked alpha channel intact
                shd_r_ch, shd_g_ch, shd_b_ch = shaded_rgb.split()
                shadow_applied_artwork = Image.merge(
                    "RGBA", (shd_r_ch, shd_g_ch, shd_b_ch, art_a)
                )

                logger.info(
                    f"[LifestylePlugin] Applied fabric shading to print layer with shadow_opacity={opacity:.2f}"
                )
            except Exception as exc:
                logger.warning(
                    f"[LifestylePlugin:{shop_id}] Could not apply shadow overlay from {shadow_path}: {exc}"
                )

        self._log_artwork_stats("04_shadow_applied_artwork", shadow_applied_artwork)
        if debug:
            shadow_applied_artwork.save(output_dir / "04_shadow_applied_artwork.png")

        # ---------------------------------------------------------------------
        # STEP 5: Composite Print Layer onto Blank Shirt Photo
        # ---------------------------------------------------------------------
        final_img = Image.alpha_composite(blank_img, shadow_applied_artwork)

        self._log_artwork_stats("05_final", final_img)
        if debug:
            final_img.save(output_dir / "05_final.png")

        out_filename = config.get("output_filename", f"{template_dir.name}.png")
        out_stem = Path(out_filename).stem
        
        # Save high-quality optimized JPEG (Quality 93) to keep size at ~1.2MB - 1.8MB (well below Etsy 10MB limit)
        jpg_out_file = output_dir / f"{out_stem}.jpg"
        rgb_final = final_img.convert("RGB")
        rgb_final.save(jpg_out_file, "JPEG", quality=93, optimize=True)

        # Also save PNG if output_filename explicitly specifies .png
        out_file = output_dir / out_filename
        final_img.save(out_file, "PNG")

        logger.info(
            f"[LifestylePlugin:{shop_id}] Successfully rendered '{template_dir.name}' lifestyle mockup "
            f"-> {jpg_out_file.name} ({jpg_out_file.stat().st_size / 1024 / 1024:.2f} MB)"
        )
        return [jpg_out_file, out_file]

    def _parse_corners(
        self, print_area: dict[str, Any], canvas_size: tuple[int, int]
    ) -> list[tuple[float, float]]:
        """Parse print area corners from config into pixel (x, y) floats."""
        raw_corners = print_area.get("corners", [])
        res_w, res_h = canvas_size
        parsed: list[tuple[float, float]] = []

        for item in raw_corners:
            if isinstance(item, dict):
                x_val = float(item.get("x", 0.0))
                y_val = float(item.get("y", 0.0))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                x_val = float(item[0])
                y_val = float(item[1])
            else:
                continue

            # Convert percentage coordinates (<= 100.0) to absolute pixels
            if x_val <= 100.0 and y_val <= 100.0:
                pixel_x = (x_val / 100.0) * res_w
                pixel_y = (y_val / 100.0) * res_h
            else:
                pixel_x = x_val
                pixel_y = y_val

            parsed.append((pixel_x, pixel_y))

        if len(parsed) < 4:
            # Default box fallback
            parsed = [
                (res_w * 0.25, res_h * 0.25),
                (res_w * 0.75, res_h * 0.25),
                (res_w * 0.75, res_h * 0.75),
                (res_w * 0.25, res_h * 0.75),
            ]
        return parsed

    def _warp_perspective_rgba(
        self,
        artwork_rgba: Image.Image,
        corners: list[tuple[float, float]],
        canvas_size: tuple[int, int],
    ) -> Image.Image:
        """Perspective-warp RGBA artwork onto canvas using OpenCV or PIL fallback."""
        canvas_w, canvas_h = canvas_size
        w, h = artwork_rgba.size

        if HAS_OPENCV and len(corners) >= 4:
            try:
                src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
                dst_pts = np.float32(corners[:4])

                # Convert PIL RGBA array (uint8)
                arr = np.array(artwork_rgba)

                # Compute perspective transformation matrix
                matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

                # Warp RGBA channels directly with zero-padding border
                warped_arr = cv2.warpPerspective(
                    arr,
                    matrix,
                    (canvas_w, canvas_h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0, 0, 0, 0),
                )

                return Image.fromarray(warped_arr, "RGBA")
            except Exception as exc:
                logger.warning(
                    f"[LifestylePlugin] OpenCV perspective warp failed ({exc}). Falling back to BBox."
                )

        # Fallback: bounding box resize & paste
        x_coords = [c[0] for c in corners]
        y_coords = [c[1] for c in corners]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        target_w = max(1, int(max_x - min_x))
        target_h = max(1, int(max_y - min_y))

        resized = artwork_rgba.resize((target_w, target_h), Image.Resampling.LANCZOS)
        full_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        full_canvas.paste(resized, (int(min_x), int(min_y)), resized)
        return full_canvas

    def _build_collage(
        self, image_paths: list[Path], target_size: tuple[int, int]
    ) -> Image.Image:
        """Create a multi-image grid collage from transparent PNG assets preserving RGBA."""
        w, h = target_size
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

        count = len(image_paths)
        if count == 0:
            return canvas

        cols = math.ceil(math.sqrt(count))
        rows = math.ceil(count / cols)

        cell_w = w // cols
        cell_h = h // rows

        for idx, img_p in enumerate(image_paths):
            row = idx // cols
            col = idx % cols

            try:
                img = Image.open(img_p).convert("RGBA")
                img.thumbnail((cell_w - 12, cell_h - 12), Image.Resampling.LANCZOS)
                paste_x = col * cell_w + (cell_w - img.width) // 2
                paste_y = row * cell_h + (cell_h - img.height) // 2
                canvas.paste(img, (paste_x, paste_y), img)
            except Exception as exc:
                logger.warning(f"[LifestylePlugin] Failed to read asset {img_p}: {exc}")
                continue

        return canvas

    def _log_artwork_stats(self, step_name: str, img: Image.Image) -> None:
        """Calculate and log dimensions, alpha range, and transparent pixel count."""
        try:
            w, h = img.size
            if img.mode == "RGBA":
                alpha_arr = np.array(img.split()[-1])
                min_alpha = int(np.min(alpha_arr))
                max_alpha = int(np.max(alpha_arr))
                transparent_pixels = int(np.sum(alpha_arr == 0))
                opaque_pixels = int(np.sum(alpha_arr > 0))
            else:
                min_alpha, max_alpha, transparent_pixels, opaque_pixels = 255, 255, 0, w * h

            logger.info(
                f"[LifestylePlugin:{step_name}] Dims: {w}x{h}, Mode: {img.mode}, "
                f"Alpha Min/Max: {min_alpha}/{max_alpha}, "
                f"Transparent Pixels: {transparent_pixels} ({transparent_pixels/(w*h)*100:.1f}%), "
                f"Opaque Pixels: {opaque_pixels}"
            )
        except Exception as exc:
            logger.debug(f"[LifestylePlugin:{step_name}] Could not log stats: {exc}")
