"""WallArtLayout strategy — stub for future multi-clipart wall art grid rendering."""

from __future__ import annotations

from pathlib import Path

from etsy_pipeline.utils.exceptions import RenderingPluginError
from rendering.plugins.layout_strategies.base_layout import LifestyleLayoutStrategy


class WallArtLayout(LifestyleLayoutStrategy):
    """Layout strategy for rendering multiple clipart items on wall art surfaces."""

    def render(
        self,
        asset_dir: Path,
        output_dir: Path,
        template_dir: Path,
        theme_name: str,
        shop_id: str,
        **kwargs,
    ) -> list[Path]:
        """Stub implementation for future multi-wall-art rendering."""
        raise RenderingPluginError(
            "WallArtLayout",
            f"WallArtLayout strategy for product '{template_dir.name}' is scheduled for future release. "
            "Please set layout: 'single_product' in shop_config.yaml."
        )
