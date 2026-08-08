"""Lifestyle Orchestrator — manages smart theme classification, bucket lookup, coverage checks, and strategy dispatching.

Handles:
  1. Character image sampling and visual theme classification into 4 groups.
  2. O(1) Bucket lookup of matching lifestyle surfaces via SurfaceGroupIndex.
  3. Coverage gap checking (logs warning and DB gap data if surfaces < 6, renders available 4-5).
  4. Strategy pattern dispatching (SingleProductLayout / WallArtLayout).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from etsy_pipeline.utils.exceptions import (
    InsufficientMockupCoverageError,
    RenderingPluginError,
)
from etsy_pipeline.utils.logging import get_logger
from rendering.compatibility.surface_group_index import SurfaceGroupIndex
from rendering.compatibility.theme_classifier import ThemeClassifier
from rendering.config.shop_config import LifestyleItemConfig
from rendering.plugins.layout_strategies.base_layout import LifestyleLayoutStrategy
from rendering.plugins.layout_strategies.single_product_layout import SingleProductLayout
from rendering.plugins.layout_strategies.wall_art_layout import WallArtLayout

logger = get_logger(__name__)


class LifestyleOrchestrator:
    """Smart orchestrator for lifestyle product mockup generation."""

    MIN_SURFACES_REQUIRED = 6
    MAX_SURFACES_TO_RENDER = 10

    def __init__(self, rendering_root: Path) -> None:
        """Initialize LifestyleOrchestrator.

        Args:
            rendering_root: Absolute path to etsy mockup creator/rendering/ directory.
        """
        self._root = rendering_root
        self._products_dir = self._root / "lifestyle_products"
        self._index = SurfaceGroupIndex(self._products_dir)

    def _get_layout_strategy(self, layout_name: str) -> LifestyleLayoutStrategy:
        """Factory method to resolve layout strategy instance."""
        layout_clean = layout_name.lower().strip()
        if layout_clean == "wall_art":
            return WallArtLayout()
        return SingleProductLayout()

    def run(
        self,
        shop_id: str,
        asset_dir: Path,
        output_dir: Path,
        theme_name: str,
        product_configs: list[LifestyleItemConfig],
    ) -> tuple[list[Path], InsufficientMockupCoverageError | None]:
        """Classify theme, select matching surfaces, gate coverage, and dispatch rendering.

        Args:
            shop_id: Shop identifier.
            asset_dir: Path to PNG clipart assets (prefers 4K upscaled directory).
            output_dir: Root output directory for rendered lifestyle mockups.
            theme_name: Human readable theme display name.
            product_configs: List of LifestyleItemConfig entries from shop_config.yaml.

        Returns:
            Tuple of (all_output_file_paths, optional_coverage_error_if_gap).
        """
        logger.info(
            f"[LifestyleOrchestrator:{shop_id}] Starting smart lifestyle mockup pipeline for '{theme_name}'"
        )

        # Step 1: Classify Theme Visual Profile
        try:
            classification = ThemeClassifier.classify_theme(asset_dir)
        except Exception as exc:
            error_msg = f"Failed to classify theme visual profile: {exc}"
            logger.error(f"[LifestyleOrchestrator:{shop_id}] {error_msg}")
            raise RenderingPluginError("LifestyleOrchestrator", error_msg) from exc

        theme_group = classification.theme_group
        logger.info(
            f"[LifestyleOrchestrator:{shop_id}] Theme Group: '{theme_group}' | "
            f"Brightness={classification.avg_brightness:.2f}, Saturation={classification.avg_saturation:.2f}"
        )

        # Step 2: Bucket Lookup — Get surfaces matching group
        matching_surfaces = self._index.get_surfaces_for_group(theme_group)

        # Filter matching surfaces to only those enabled in product_configs (if list is non-empty)
        enabled_names = {p.name for p in product_configs} if product_configs else set()
        if enabled_names:
            selected_surfaces = [s for s in matching_surfaces if s in enabled_names]
            # If enabled_names resulted in 0, fall back to matching_surfaces
            if not selected_surfaces:
                selected_surfaces = matching_surfaces
        else:
            selected_surfaces = matching_surfaces

        available_count = len(selected_surfaces)
        coverage_error: InsufficientMockupCoverageError | None = None

        # Step 3: Coverage Gap Gate (< 6 surfaces)
        if available_count < self.MIN_SURFACES_REQUIRED:
            missing_specs = [
                {
                    "product_type": "tshirt",
                    "required_compatibility_groups": [theme_group],
                    "recommendation": f"Add {self.MIN_SURFACES_REQUIRED - available_count} more surface(s) to '{theme_group}' group",
                }
            ]
            coverage_error = InsufficientMockupCoverageError(
                theme_slug=theme_name,
                theme_group=theme_group,
                surfaces_available=available_count,
                surfaces_needed=self.MIN_SURFACES_REQUIRED,
                missing_surface_specs=missing_specs,
            )
            logger.warning(
                f"[LifestyleOrchestrator:{shop_id}] Coverage Gap: Only {available_count}/"
                f"{self.MIN_SURFACES_REQUIRED} surfaces available for group '{theme_group}'. "
                "Rendering available surfaces and logging DB gap data."
            )

        # Cap at MAX (10)
        final_surfaces = selected_surfaces[: self.MAX_SURFACES_TO_RENDER]
        logger.info(
            f"[LifestyleOrchestrator:{shop_id}] Selected {len(final_surfaces)} surface(s) for rendering: {final_surfaces}"
        )

        # Map product config strategy per surface
        config_map = {p.name: p for p in product_configs}

        all_outputs: list[Path] = []
        for surface_name in final_surfaces:
            surface_template_dir = self._products_dir / surface_name
            if not surface_template_dir.exists():
                logger.warning(
                    f"[LifestyleOrchestrator:{shop_id}] Surface directory missing at {surface_template_dir}. Skipping."
                )
                continue

            item_cfg = config_map.get(surface_name)
            layout_name = item_cfg.layout if item_cfg else "single_product"
            strategy = self._get_layout_strategy(layout_name)

            product_out_dir = output_dir / surface_name
            try:
                outputs = strategy.render(
                    asset_dir=asset_dir,
                    output_dir=product_out_dir,
                    template_dir=surface_template_dir,
                    theme_name=theme_name,
                    shop_id=shop_id,
                )
                all_outputs.extend(outputs)
            except Exception as exc:
                logger.error(
                    f"[LifestyleOrchestrator:{shop_id}] Failed to render surface '{surface_name}': {exc}"
                )

        logger.info(
            f"[LifestyleOrchestrator:{shop_id}] Rendered {len(final_surfaces)} lifestyle surface(s), "
            f"produced {len(all_outputs)} output files."
        )
        return all_outputs, coverage_error
