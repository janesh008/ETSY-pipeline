"""Pydantic model for loading and validating shop configuration YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class HeroConfig(BaseModel):
    """Configuration for hero mockups."""

    templates_dir: str = Field(
        ...,
        description="Relative path to the shop's templates directory containing JSON layouts.",
    )


class LifestyleItemConfig(BaseModel):
    """Configuration for an individual lifestyle product entry."""

    name: str = Field(..., description="Surface directory folder name (e.g. 'black_t-shirt_1')")
    layout: str = Field(default="single_product", description="Rendering layout strategy ('single_product' or 'wall_art')")
    wall_art_count: int = Field(default=4, description="Number of clipart items to arrange if layout is 'wall_art'")


class LifestyleConfig(BaseModel):
    """Configuration for lifestyle product mockups."""

    enabled: bool = Field(default=False)
    products: List[Any] = Field(default_factory=list)

    def get_product_configs(self) -> List[LifestyleItemConfig]:
        """Normalize products list into LifestyleItemConfig instances."""
        items: List[LifestyleItemConfig] = []
        for p in self.products:
            if isinstance(p, str):
                items.append(LifestyleItemConfig(name=p))
            elif isinstance(p, dict):
                items.append(LifestyleItemConfig(**p))
        return items


class MockupConfig(BaseModel):
    """Container for mockup generator settings."""

    hero: Optional[HeroConfig] = None
    lifestyle: LifestyleConfig = Field(default_factory=LifestyleConfig)


class MetadataConfig(BaseModel):
    """Configuration for AI-driven SEO metadata generation."""

    prompt_file: Optional[str] = Field(
        default=None,
        description="Relative path to shop-specific Gemini prompt file.",
    )
    seo_mode: bool = Field(
        default=True,
        description="Enforces strict SEO keyword ranking logic.",
    )


class ShopConfig(BaseModel):
    """Central shop configuration loaded from shop_config.yaml."""

    shop_id: str = Field(..., description="Unique shop identifier (e.g. 'luna_cliparts')")
    shop_name: str = Field(..., description="Human readable shop display name")
    etsy_shop_name: Optional[str] = Field(default=None, description="Etsy shop handle/slug")

    mockups: MockupConfig = Field(default_factory=MockupConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)

    @classmethod
    def load_from_yaml(cls, yaml_path: Path) -> ShopConfig:
        """Load and validate ShopConfig from a YAML file path.

        Args:
            yaml_path: Absolute or relative path to shop_config.yaml.

        Returns:
            Validated ShopConfig instance.
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"Shop config YAML file not found: {yaml_path}")

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML content in {yaml_path}")

        return cls.model_validate(data)
