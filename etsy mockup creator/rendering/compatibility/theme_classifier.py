"""Theme Classifier — samples theme clipart and determines theme visual compatibility group.

Implements character image sampling priority:
  1. MAIN_CHARACTER images
  2. SUB_CHARACTER images
  3. GROUP_CHARACTER images
  4. Filenames containing "CHARACTER"
  5. Non-prop/pattern PNG fallbacks

Classifies into one group: 'dark_art', 'light_art', 'colorful_art', or 'medium_art'.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from etsy_pipeline.utils.logging import get_logger
from rendering.compatibility.clipart_analyzer import (
    ClipartAnalysisError,
    ClipartAnalyzer,
)

logger = get_logger(__name__)


@dataclass
class ThemeClassificationResult:
    """Dataclass holding theme visual classification results."""

    theme_group: str
    avg_brightness: float
    avg_saturation: float
    sampled_images: list[Path]


class ThemeClassifier:
    """Samples character clipart and classifies theme visual compatibility group."""

    SKIP_KEYWORDS = {"prop", "pattern", "background", "border", "element", "txt", "text"}

    @classmethod
    def sample_character_images(cls, asset_dir: Path, max_samples: int = 10) -> list[Path]:
        """Sample up to max_samples character PNG files using strict priority.

        Priority order:
          1. MAIN_CHARACTER
          2. SUB_CHARACTER
          3. GROUP_CHARACTER
          4. Any filename containing "CHARACTER"
          5. Any PNG that does not contain skip keywords

        Args:
            asset_dir: Directory containing clipart PNG files.
            max_samples: Maximum number of images to sample (default: 10).

        Returns:
            List of sampled PNG file paths.

        Raises:
            ClipartAnalysisError: If no valid clipart PNGs are found.
        """
        all_pngs = sorted(list(asset_dir.rglob("*.png")))
        if not all_pngs:
            raise ClipartAnalysisError(f"No PNG assets found in '{asset_dir}'.")

        main_chars: list[Path] = []
        sub_chars: list[Path] = []
        group_chars: list[Path] = []
        other_chars: list[Path] = []
        fallbacks: list[Path] = []

        for p in all_pngs:
            fname = p.name.lower()

            # Skip props, patterns, backgrounds
            if any(kw in fname for kw in cls.SKIP_KEYWORDS):
                continue

            if "main_character" in fname:
                main_chars.append(p)
            elif "sub_character" in fname:
                sub_chars.append(p)
            elif "group_character" in fname:
                group_chars.append(p)
            elif "character" in fname:
                other_chars.append(p)
            else:
                fallbacks.append(p)

        sampled: list[Path] = []
        for bucket in (main_chars, sub_chars, group_chars, other_chars, fallbacks):
            for img_path in bucket:
                if img_path not in sampled:
                    sampled.append(img_path)
                if len(sampled) >= max_samples:
                    break
            if len(sampled) >= max_samples:
                break

        if not sampled:
            # Absolute fallback: return first max_samples PNGs
            sampled = all_pngs[:max_samples]

        logger.info(
            f"[ThemeClassifier] Sampled {len(sampled)} character images from {len(all_pngs)} total PNGs"
        )
        return sampled

    @classmethod
    def classify_theme(cls, asset_dir: Path) -> ThemeClassificationResult:
        """Analyze sampled theme clipart and return classification group.

        Args:
            asset_dir: Directory containing clipart PNG files.

        Returns:
            ThemeClassificationResult instance.
        """
        sampled_images = cls.sample_character_images(asset_dir, max_samples=10)

        brightness_list: list[float] = []
        saturation_list: list[float] = []

        for img_p in sampled_images:
            try:
                analysis = ClipartAnalyzer.analyze_clipart(img_p)
                brightness_list.append(analysis.average_brightness)
                saturation_list.append(analysis.saturation)
            except Exception as exc:
                logger.warning(
                    f"[ThemeClassifier] Failed to analyze '{img_p.name}': {exc}"
                )

        if not brightness_list:
            avg_brightness = 0.50
            avg_saturation = 0.50
        else:
            avg_brightness = float(sum(brightness_list) / len(brightness_list))
            avg_saturation = float(sum(saturation_list) / len(saturation_list))

        # Classification rules
        if avg_brightness < 0.35:
            theme_group = "dark_art"
        elif avg_brightness > 0.70:
            theme_group = "light_art"
        elif avg_saturation > 0.65:
            theme_group = "colorful_art"
        else:
            theme_group = "medium_art"

        logger.info(
            f"[ThemeClassifier] Theme classified as '{theme_group}' | "
            f"avg_brightness={avg_brightness:.2f}, avg_saturation={avg_saturation:.2f}"
        )

        return ThemeClassificationResult(
            theme_group=theme_group,
            avg_brightness=avg_brightness,
            avg_saturation=avg_saturation,
            sampled_images=sampled_images,
        )
