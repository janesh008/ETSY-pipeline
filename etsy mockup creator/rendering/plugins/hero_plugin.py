"""HeroPlugin — wraps the existing etsy mockup creator subprocess.

Calls src/main.py with a shop-specific --templates directory.
The underlying rendering engine (src/*.py) is never modified.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from etsy_pipeline.utils.exceptions import RenderingPluginError
from etsy_pipeline.utils.logging import get_logger
from rendering.plugins.base_plugin import BasePlugin

logger = get_logger(__name__)


class HeroPlugin(BasePlugin):
    """Generates hero + category mockups using the existing subprocess renderer.

    The only difference from the original MockupWorker._run_mockup_creator() call
    is that --templates now points to the shop's own templates/ directory instead
    of the root-level templates/ folder.
    """

    def render(
        self,
        asset_dir: Path,
        output_dir: Path,
        template_dir: Path,
        theme_name: str,
        shop_id: str,
    ) -> list[Path]:
        """Run the mockup creator subprocess with the shop's template directory.

        Args:
            asset_dir: Path to no_bg/ transparent PNGs.
            output_dir: Where to write rendered mockup PNGs.
            template_dir: Path to this shop's templates/ folder.
            theme_name: Theme display name for text interpolation.
            shop_id: Shop identifier (for logging).

        Returns:
            List of all generated PNG file paths.

        Raises:
            RenderingPluginError: If template_dir or asset_dir is missing,
                                   or if the subprocess fails.
        """
        mockup_creator_dir = Path(__file__).resolve().parent.parent.parent

        if not asset_dir.exists():
            error_msg = f"Asset directory for shop '{shop_id}' does not exist: {asset_dir}"
            logger.error(f"[HeroPlugin:{shop_id}] {error_msg}")
            raise RenderingPluginError("HeroPlugin", error_msg)

        if not template_dir.exists():
            error_msg = f"Templates directory for shop '{shop_id}' does not exist: {template_dir}"
            logger.error(f"[HeroPlugin:{shop_id}] {error_msg}")
            raise RenderingPluginError("HeroPlugin", error_msg)

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[HeroPlugin:{shop_id}] Running hero mockup generator subprocess. "
            f"Asset dir: {asset_dir}, Templates: {template_dir}"
        )

        cmd = [
            sys.executable,
            "-m",
            "src.main",
            "--theme",
            str(asset_dir.resolve()),
            "--output",
            str(output_dir.resolve()),
            "--templates",
            str(template_dir.resolve()),
        ]
        if theme_name and theme_name.strip():
            cmd.extend(["--theme-name", theme_name.strip()])

        try:
            result = subprocess.run(
                cmd,
                cwd=str(mockup_creator_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"[HeroPlugin:{shop_id}] Subprocess completed successfully.")
            if result.stdout:
                logger.debug(f"[HeroPlugin:{shop_id}] stdout:\n{result.stdout}")
        except subprocess.CalledProcessError as exc:
            error_details = exc.stderr or exc.stdout or str(exc)
            error_msg = f"Hero mockup subprocess failed for shop '{shop_id}': {error_details}"
            logger.error(f"[HeroPlugin:{shop_id}] {error_msg}")
            raise RenderingPluginError("HeroPlugin", error_msg) from exc
        except Exception as exc:
            error_msg = f"Unexpected error during hero rendering for shop '{shop_id}': {exc}"
            logger.error(f"[HeroPlugin:{shop_id}] {error_msg}")
            raise RenderingPluginError("HeroPlugin", error_msg) from exc

        rendered_files = sorted(list(output_dir.glob("*.jpg")) + list(output_dir.glob("*.png")))
        if not rendered_files:
            logger.warning(
                f"[HeroPlugin:{shop_id}] Subprocess succeeded but no files were produced in {output_dir}"
            )

        return rendered_files
