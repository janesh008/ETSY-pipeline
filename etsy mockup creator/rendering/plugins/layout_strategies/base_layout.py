"""Abstract Base Class for Lifestyle Layout Strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class LifestyleLayoutStrategy(ABC):
    """Abstract interface for lifestyle mockup rendering strategies."""

    @abstractmethod
    def render(
        self,
        asset_dir: Path,
        output_dir: Path,
        template_dir: Path,
        theme_name: str,
        shop_id: str,
        **kwargs,
    ) -> list[Path]:
        """Render lifestyle mockup using this strategy.

        Args:
            asset_dir: Path to transparent PNG clipart assets.
            output_dir: Output directory for rendered mockups.
            template_dir: Surface template folder (e.g. lifestyle_products/black_t-shirt_1).
            theme_name: Display name for theme.
            shop_id: Shop identifier.

        Returns:
            List of generated output file paths.
        """
        pass
