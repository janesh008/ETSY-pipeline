"""Abstract base class for all rendering plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class BasePlugin(ABC):
    """Abstract base for all mockup rendering plugins.

    Every plugin receives the same inputs and returns a list of output file paths.
    No plugin has any knowledge of other plugins or the pipeline orchestrator.

    To implement a new plugin:
        1. Subclass BasePlugin
        2. Implement render()
        3. Register it in orchestrator.py
    """

    @abstractmethod
    def render(
        self,
        asset_dir: Path,
        output_dir: Path,
        template_dir: Path,
        theme_name: str,
        shop_id: str,
    ) -> list[Path]:
        """Render mockups and return list of output file paths.

        Args:
            asset_dir: Path to the no_bg/ folder containing transparent PNGs.
            output_dir: Directory where rendered outputs should be saved.
            template_dir: Path to this plugin's template folder (shop-specific).
            theme_name: Human-readable theme name for text interpolation.
            shop_id: The shop identifier (e.g. 'luna_cliparts').

        Returns:
            List of absolute Paths to all rendered output files.
        """
