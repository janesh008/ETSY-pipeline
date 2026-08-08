"""Rendering orchestrator — reads shop config and dispatches plugins.

Usage:
    from rendering.plugins.orchestrator import RenderingOrchestrator

    orchestrator = RenderingOrchestrator(rendering_root=Path("etsy mockup creator/rendering"))
    outputs = orchestrator.run(
        shop_id="luna_cliparts",
        asset_dir=no_bg_dir,
        output_dir=mockups_dir,
        theme_name="Red Jersey Ronaldo",
    )
"""

from __future__ import annotations

from pathlib import Path

from etsy_pipeline.utils.exceptions import MockupGenerationError
from etsy_pipeline.utils.logging import get_logger
from rendering.config.shop_config import ShopConfig
from rendering.plugins.hero_plugin import HeroPlugin
from rendering.plugins.lifestyle_plugin import LifestylePlugin

logger = get_logger(__name__)


class RenderingOrchestrator:
    """Reads shop_config.yaml and dispatches the appropriate plugins.

    Does not contain rendering logic. Only coordinates plugin dispatch.
    """

    def __init__(self, rendering_root: Path) -> None:
        """Initialise RenderingOrchestrator.

        Args:
            rendering_root: Absolute path to the rendering/ directory
                            (etsy mockup creator/rendering/).
        """
        self._root = rendering_root

    def run(
        self,
        shop_id: str,
        asset_dir: Path,
        output_dir: Path,
        theme_name: str,
        upscaled_asset_dir: Path | None = None,
    ) -> list[Path]:
        """Dispatch plugins for the given shop and return all output paths.

        Args:
            shop_id: The shop identifier (e.g. 'luna_cliparts').
            asset_dir: Path to no_bg/ transparent PNGs (used for Hero templates).
            output_dir: Root output directory for this shop's rendered files.
            theme_name: Human-readable theme name.
            upscaled_asset_dir: Optional path to 4K upscaled PNGs (used for Lifestyle photos).

        Returns:
            List of all generated output file paths.

        Raises:
            MockupGenerationError: If shop config resolution or plugin rendering fails.
        """
        logger.info(
            f"[RenderingOrchestrator] Dispatching rendering pipeline for shop '{shop_id}'"
        )
        config = self._load_shop_config(shop_id)
        all_outputs: list[Path] = []

        # --- Hero Plugin (Uses no_bg / 700px assets for low RAM grid rendering) ---
        if config.mockups.hero and config.mockups.hero.templates_dir:
            t_path = Path(config.mockups.hero.templates_dir)
            if t_path.is_absolute():
                templates_dir = t_path
            elif t_path.parts and t_path.parts[0] == "rendering":
                templates_dir = self._root.parent / t_path
            else:
                templates_dir = self._root / t_path

            hero_output = output_dir / "mockups"
            logger.info(
                f"[RenderingOrchestrator:{shop_id}] Running HeroPlugin with templates at {templates_dir}"
            )
            plugin = HeroPlugin()
            outputs = plugin.render(
                asset_dir=asset_dir,
                output_dir=hero_output,
                template_dir=templates_dir,
                theme_name=theme_name,
                shop_id=shop_id,
            )
            all_outputs.extend(outputs)

        # --- Lifestyle Orchestrator (Prefers upscaled / 4K assets for photorealistic prints) ---
        if config.mockups.lifestyle and config.mockups.lifestyle.enabled:
            # Determine asset directory for lifestyle photos (upscaled if available and non-empty, else asset_dir)
            lifestyle_asset_dir = asset_dir
            if upscaled_asset_dir and upscaled_asset_dir.exists() and list(upscaled_asset_dir.glob("*.png")):
                logger.info(
                    f"[RenderingOrchestrator:{shop_id}] Using 4K upscaled assets from '{upscaled_asset_dir.name}' for Lifestyle mockups"
                )
                lifestyle_asset_dir = upscaled_asset_dir
            else:
                logger.info(
                    f"[RenderingOrchestrator:{shop_id}] Using standard assets from '{asset_dir.name}' for Lifestyle mockups"
                )

            from rendering.plugins.lifestyle_orchestrator import LifestyleOrchestrator

            product_configs = config.mockups.lifestyle.get_product_configs()
            lifestyle_output = output_dir / "lifestyle_mockups"

            orchestrator = LifestyleOrchestrator(self._root)
            lifestyle_outputs, coverage_error = orchestrator.run(
                shop_id=shop_id,
                asset_dir=lifestyle_asset_dir,
                output_dir=lifestyle_output,
                theme_name=theme_name,
                product_configs=product_configs,
            )
            all_outputs.extend(lifestyle_outputs)

        logger.info(
            f"[RenderingOrchestrator:{shop_id}] Rendering complete. Generated {len(all_outputs)} total outputs."
        )
        return all_outputs

    def _load_shop_config(self, shop_id: str) -> ShopConfig:
        """Load and return the shop YAML config as a ShopConfig instance.

        Args:
            shop_id: The shop identifier.

        Returns:
            Validated ShopConfig instance.

        Raises:
            MockupGenerationError: If shop_config.yaml is not found or malformed.
        """
        shops_dir = self._root / "shops"
        if not shops_dir.exists():
            error_msg = f"Shops directory does not exist at: {shops_dir}"
            logger.error(f"[RenderingOrchestrator] {error_msg}")
            raise MockupGenerationError(error_msg)

        for shop_dir in shops_dir.iterdir():
            if shop_dir.is_dir():
                candidate = shop_dir / "shop_config.yaml"
                if candidate.exists():
                    try:
                        cfg = ShopConfig.load_from_yaml(candidate)
                        if cfg.shop_id == shop_id:
                            return cfg
                    except Exception as exc:
                        logger.warning(
                            f"[RenderingOrchestrator] Error reading candidate {candidate}: {exc}"
                        )
                        continue

        error_msg = f"No valid shop_config.yaml found for shop_id='{shop_id}' in {shops_dir}"
        logger.error(f"[RenderingOrchestrator] {error_msg}")
        raise MockupGenerationError(error_msg)
