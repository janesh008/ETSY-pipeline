"""Surface Group Index — indexes lifestyle product surfaces by compatibility group.

Scans all lifestyle product subdirectories and reads metadata.json to build O(1) group buckets.
Raises MissingSurfaceGroupError if compatibility_groups is missing in metadata.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from etsy_pipeline.utils.exceptions import MissingSurfaceGroupError
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


class SurfaceGroupIndex:
    """Indexes lifestyle surfaces by compatibility groups for O(1) bucket lookups."""

    def __init__(self, lifestyle_products_dir: Path) -> None:
        """Initialize and build the surface index.

        Args:
            lifestyle_products_dir: Directory containing lifestyle product folders.
        """
        self._dir = lifestyle_products_dir
        self._index: dict[str, list[str]] = {
            "dark_art": [],
            "light_art": [],
            "colorful_art": [],
            "medium_art": [],
        }
        self.build()

    def build(self) -> None:
        """Scan lifestyle products directory and index all surfaces by group."""
        if not self._dir.exists():
            logger.warning(
                f"[SurfaceGroupIndex] Directory does not exist: {self._dir}"
            )
            return

        count = 0
        for entry in sorted(self._dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue

            meta_path = entry / "metadata.json"
            if not meta_path.exists():
                raise MissingSurfaceGroupError(entry.name, str(meta_path))

            try:
                meta_dict = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise MissingSurfaceGroupError(entry.name, str(meta_path)) from exc

            groups = meta_dict.get("compatibility_groups")
            if not groups or not isinstance(groups, list):
                raise MissingSurfaceGroupError(entry.name, str(meta_path))

            for group in groups:
                if group not in self._index:
                    self._index[group] = []
                if entry.name not in self._index[group]:
                    self._index[group].append(entry.name)

            count += 1

        logger.info(
            f"[SurfaceGroupIndex] Successfully indexed {count} surfaces into groups: "
            f"dark_art={len(self._index.get('dark_art', []))}, "
            f"light_art={len(self._index.get('light_art', []))}, "
            f"colorful_art={len(self._index.get('colorful_art', []))}, "
            f"medium_art={len(self._index.get('medium_art', []))}"
        )

    def get_surfaces_for_group(self, group: str) -> list[str]:
        """Get matching surface folder names for a given group.

        Args:
            group: Group name ('dark_art', 'light_art', 'colorful_art', 'medium_art').

        Returns:
            List of matching surface folder names.
        """
        surfaces = self._index.get(group, [])
        if not surfaces:
            # Fallback to medium_art if group is empty
            surfaces = self._index.get("medium_art", [])
        return surfaces
