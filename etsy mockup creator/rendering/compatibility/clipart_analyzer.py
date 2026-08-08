"""Clipart Visual Analyzer Module.

Extracts visual features (colors, brightness, saturation, contrast, complexity,
aspect ratio, and preferred surface colors) from transparent RGBA PNG clipart assets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np
from PIL import Image

from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


class ClipartAnalysisError(Exception):
    """Raised when visual clipart analysis fails."""


@dataclass
class ClipartAnalysis:
    """Dataclass holding extracted visual metrics for clipart artwork."""

    dominant_colors: list[str]  # Hex color codes (e.g. ["#1A1A1A", "#8B0000"])
    average_brightness: float  # Perceived luminance 0.0 - 1.0
    brightness_category: str  # "dark", "medium", "light"
    color_temperature: str  # "warm", "cool", "neutral"
    saturation: float  # Mean saturation 0.0 - 1.0
    saturation_category: str  # "low", "medium", "high"
    contrast: float  # Luminance standard deviation 0.0 - 1.0
    transparency: float  # Ratio of non-transparent pixels in bbox
    visual_complexity: float  # Edge density score 0.0 - 1.0
    complexity_category: str  # "minimal", "moderate", "detailed"
    artwork_bbox: tuple[int, int, int, int]  # (min_x, min_y, max_x, max_y)
    aspect_ratio: float  # bbox width / bbox height
    estimated_print_area: float  # bbox area / total canvas area
    preferred_product_colors: list[str]  # e.g. ["white", "cream", "light_grey"]

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics dataclass to dictionary."""
        return asdict(self)


class ClipartAnalyzer:
    """Analyzer for extracting visual attributes from transparent PNG artwork."""

    @staticmethod
    def analyze_clipart(image_source: str | Path | Image.Image) -> ClipartAnalysis:
        """Extract visual attributes from a transparent PNG image.

        Args:
            image_source: Path to PNG image or PIL Image instance.

        Returns:
            ClipartAnalysis containing calculated visual metrics.
        """
        logger.info(f"[ClipartAnalyzer] Starting visual analysis for clipart: {image_source if isinstance(image_source, (str, Path)) else 'PIL Image'}")
        
        try:
            if isinstance(image_source, (str, Path)):
                img_path = Path(image_source)
                if not img_path.exists():
                    raise ClipartAnalysisError(f"Clipart image file not found: {img_path}")
                img = Image.open(img_path)
            else:
                img = image_source

            if img.mode != "RGBA":
                img = img.convert("RGBA")

            img_arr = np.array(img)
            height, width, _ = img_arr.shape
            total_pixels = height * width

            r_chan = img_arr[:, :, 0]
            g_chan = img_arr[:, :, 1]
            b_chan = img_arr[:, :, 2]
            alpha = img_arr[:, :, 3]

            non_transparent_mask = alpha > 10
            opaque_count = int(np.sum(non_transparent_mask))

            if opaque_count == 0:
                raise ClipartAnalysisError("Clipart image contains zero non-transparent pixels.")

            # Bounding Box calculation
            y_indices, x_indices = np.where(non_transparent_mask)
            min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
            min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))
            bbox = (min_x, min_y, max_x, max_y)

            bbox_w = max(1, max_x - min_x + 1)
            bbox_h = max(1, max_y - min_y + 1)
            aspect_ratio = round(bbox_w / bbox_h, 3)
            bbox_area = bbox_w * bbox_h
            estimated_print_area = round(bbox_area / total_pixels, 3)
            transparency = round(opaque_count / bbox_area, 3)

            # Perceived Luminance ($0.299R + 0.587G + 0.114B$)
            lum_arr = (0.299 * r_chan + 0.587 * g_chan + 0.114 * b_chan) / 255.0
            opaque_lum = lum_arr[non_transparent_mask]

            average_brightness = round(float(np.mean(opaque_lum)), 3)
            contrast = round(float(np.std(opaque_lum)), 3)

            if average_brightness < 0.38:
                brightness_category = "dark"
            elif average_brightness > 0.68:
                brightness_category = "light"
            else:
                brightness_category = "medium"

            # HSV Saturation & Temperature
            hsv_arr = cv2.cvtColor(img_arr[:, :, :3], cv2.COLOR_RGB2HSV)
            h_chan = hsv_arr[:, :, 0]
            s_chan = hsv_arr[:, :, 1] / 255.0

            opaque_s = s_chan[non_transparent_mask]
            saturation = round(float(np.mean(opaque_s)), 3)

            if saturation < 0.25:
                saturation_category = "low"
            elif saturation > 0.60:
                saturation_category = "high"
            else:
                saturation_category = "medium"

            # Color Temperature calculation
            opaque_h = h_chan[non_transparent_mask]
            # Warm hues: Red (0-30, 150-180), Yellow/Orange (30-60)
            warm_pixels = np.sum((opaque_h < 35) | (opaque_h > 145))
            cool_pixels = np.sum((opaque_h >= 35) & (opaque_h <= 145))
            if warm_pixels > cool_pixels * 1.3:
                color_temperature = "warm"
            elif cool_pixels > warm_pixels * 1.3:
                color_temperature = "cool"
            else:
                color_temperature = "neutral"

            # Dominant Colors Extraction
            opaque_rgb = img_arr[non_transparent_mask][:, :3]
            dominant_colors = ClipartAnalyzer._extract_dominant_colors(opaque_rgb)

            # Visual Complexity (Sobel edge magnitude on opaque alpha & luminance)
            gray = cv2.cvtColor(img_arr[:, :, :3], cv2.COLOR_RGB2GRAY)
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            edge_mag = np.sqrt(sobel_x**2 + sobel_y**2)
            opaque_edges = edge_mag[non_transparent_mask]
            visual_complexity = round(float(np.mean(opaque_edges)) / 255.0, 3)

            if visual_complexity < 0.15:
                complexity_category = "minimal"
            elif visual_complexity > 0.40:
                complexity_category = "detailed"
            else:
                complexity_category = "moderate"

            # Preferred Product Surface Colors
            preferred_product_colors = ClipartAnalyzer._infer_preferred_product_colors(
                brightness_category, saturation_category, dominant_colors
            )

            analysis = ClipartAnalysis(
                dominant_colors=dominant_colors,
                average_brightness=average_brightness,
                brightness_category=brightness_category,
                color_temperature=color_temperature,
                saturation=saturation,
                saturation_category=saturation_category,
                contrast=contrast,
                transparency=transparency,
                visual_complexity=visual_complexity,
                complexity_category=complexity_category,
                artwork_bbox=bbox,
                aspect_ratio=aspect_ratio,
                estimated_print_area=estimated_print_area,
                preferred_product_colors=preferred_product_colors,
            )

            logger.info(
                f"[ClipartAnalyzer] Analysis complete. Brightness: {brightness_category} ({average_brightness}), "
                f"Saturation: {saturation_category} ({saturation}), Complexity: {complexity_category}"
            )
            return analysis

        except Exception as exc:
            logger.error(f"[ClipartAnalyzer] Failed to analyze clipart: {exc}")
            raise ClipartAnalysisError(f"Visual clipart analysis failed: {exc}") from exc

    @staticmethod
    def _extract_dominant_colors(opaque_rgb: np.ndarray, num_colors: int = 5) -> list[str]:
        """Quantize pixels to find dominant Hex color strings."""
        if len(opaque_rgb) == 0:
            return ["#000000"]
        # Resample pixels for fast processing if very large
        if len(opaque_rgb) > 5000:
            indices = np.random.choice(len(opaque_rgb), 5000, replace=False)
            opaque_rgb = opaque_rgb[indices]

        pixels = np.float32(opaque_rgb)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        flags = cv2.KMEANS_RANDOM_CENTERS

        k = min(num_colors, len(opaque_rgb))
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, flags)

        # Sort centers by frequency
        counts = np.bincount(labels.flatten())
        sorted_indices = np.argsort(-counts)

        dominant_hex = []
        for idx in sorted_indices:
            r, g, b = np.uint8(centers[idx])
            dominant_hex.append(f"#{r:02X}{g:02X}{b:02X}")

        return dominant_hex

    @staticmethod
    def _infer_preferred_product_colors(
        brightness_cat: str, saturation_cat: str, dominant_colors: Sequence[str]
    ) -> list[str]:
        """Infer list of high-contrast, visually compatible product surface colors."""
        if brightness_cat == "dark":
            return ["white", "cream", "light_grey", "pastel_pink", "light_blue"]
        elif brightness_cat == "light":
            return ["black", "dark_charcoal", "navy", "deep_red", "dark_green"]
        else:  # medium
            if saturation_cat == "high":
                return ["white", "cream", "black", "dark_charcoal", "neutral_grey"]
            else:
                return ["white", "black", "dark_charcoal", "cream"]
