"""SingleProductLayout strategy — renders single clipart item onto lifestyle surface."""

from __future__ import annotations

from pathlib import Path

from rendering.plugins.layout_strategies.base_layout import LifestyleLayoutStrategy
from rendering.plugins.lifestyle_plugin import LifestylePlugin


class SingleProductLayout(LifestyleLayoutStrategy):
    """Layout strategy for single-product lifestyle mockups."""

    def __init__(self) -> None:
        self._plugin = LifestylePlugin()

    def render(
        self,
        asset_dir: Path,
        output_dir: Path,
        template_dir: Path,
        theme_name: str,
        shop_id: str,
        **kwargs,
    ) -> list[Path]:
        """Delegate rendering to LifestylePlugin."""
        return self._plugin.render(
            asset_dir=asset_dir,
            output_dir=output_dir,
            template_dir=template_dir,
            theme_name=theme_name,
            shop_id=shop_id,
        )
