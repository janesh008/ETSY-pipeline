"""Deterministic Clipart-Template Compatibility Engine.

Calculates weighted compatibility scores between extracted clipart visual metrics
and mockup template compatibility metadata. Ranks candidate templates and raises
NoCompatibleTemplateFoundError if no template satisfies visual contrast requirements.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from etsy_pipeline.utils.logging import get_logger

from .clipart_analyzer import ClipartAnalysis
from .template_schema import CompatibilityMetadata, extract_template_metadata

logger = get_logger(__name__)


class NoCompatibleTemplateFoundError(Exception):
    """Raised when no template meets the visual compatibility threshold."""

    def __init__(
        self,
        message: str,
        clipart_analysis: ClipartAnalysis,
        required_surface_recommendation: dict[str, Any],
    ) -> None:
        super().__init__(message)
        self.clipart_analysis = clipart_analysis
        self.required_surface_recommendation = required_surface_recommendation


@dataclass
class TemplateScore:
    """Dataclass holding score details for a candidate template."""

    template_id: str
    template_data: dict[str, Any]
    metadata: CompatibilityMetadata
    score: float
    score_breakdown: dict[str, float]


@dataclass
class SelectionResult:
    """Dataclass holding final template selection outcome."""

    selected_template_id: str
    selected_template_data: dict[str, Any]
    score: float
    alternatives: list[dict[str, Any]]
    analysis: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary schema."""
        return {
            "selected_template": self.selected_template_id,
            "score": round(self.score, 3),
            "alternatives": [
                {"template_id": alt["template_id"], "score": round(alt["score"], 3)}
                for alt in self.alternatives
            ],
            "analysis": self.analysis,
        }


# Perceived Luminance lookup for surface colors
COLOR_LUMINANCE = {
    "white": 0.95,
    "cream": 0.90,
    "light_grey": 0.80,
    "pastel_pink": 0.85,
    "light_blue": 0.82,
    "yellow": 0.88,
    "neutral_grey": 0.50,
    "black": 0.05,
    "dark_charcoal": 0.15,
    "navy": 0.18,
    "deep_red": 0.25,
    "dark_green": 0.20,
}


class CompatibilityEngine:
    """Engine for ranking and selecting compatible mockup templates for clipart."""

    @staticmethod
    def rank_templates(
        analysis: ClipartAnalysis,
        templates: Sequence[tuple[str, dict[str, Any]]],  # List of (file_path_or_id, template_dict)
        min_score_threshold: float = 0.50,
        override_template_id: str | None = None,
    ) -> SelectionResult:
        """Rank templates by visual compatibility with the provided clipart analysis.

        Args:
            analysis: Extracted ClipartAnalysis object.
            templates: List of (file_path, template_dict) tuples.
            min_score_threshold: Minimum passing composite score threshold.
            override_template_id: Optional template_id to force manual override.

        Returns:
            SelectionResult object containing winning template and ranked alternatives.

        Raises:
            NoCompatibleTemplateFoundError: If no template achieves min_score_threshold.
        """
        logger.info(
            f"[CompatibilityEngine] Ranking {len(templates)} templates for clipart. "
            f"Brightness: {analysis.brightness_category} ({analysis.average_brightness}), "
            f"Override: {override_template_id or 'None'}"
        )

        if not templates:
            rec = CompatibilityEngine._build_surface_recommendation(analysis)
            raise NoCompatibleTemplateFoundError(
                "No templates were provided to the compatibility engine. "
                f"Please add a mockup template matching surface recommendation: {rec}",
                clipart_analysis=analysis,
                required_surface_recommendation=rec,
            )

        scored_templates: list[TemplateScore] = []

        for item_key, t_dict in templates:
            # Extract metadata with strict validation (raises error if missing)
            metadata = extract_template_metadata(t_dict, file_path=item_key)

            # Calculate individual sub-scores
            sub_scores = CompatibilityEngine._calculate_sub_scores(analysis, metadata)

            # Weighted composite score equation:
            # S = 0.30*Contrast + 0.25*ColorSep + 0.15*Bright + 0.10*Sat + 0.10*Aspect + 0.10*Complexity
            composite_score = round(
                0.30 * sub_scores["contrast"]
                + 0.25 * sub_scores["color_separation"]
                + 0.15 * sub_scores["brightness"]
                + 0.10 * sub_scores["saturation"]
                + 0.10 * sub_scores["aspect"]
                + 0.10 * sub_scores["complexity"],
                4,
            )

            scored_templates.append(
                TemplateScore(
                    template_id=metadata.template_id,
                    template_data=t_dict,
                    metadata=metadata,
                    score=composite_score,
                    score_breakdown=sub_scores,
                )
            )

            logger.debug(
                f"[CompatibilityEngine] Template '{metadata.template_id}' ({metadata.product_color}) "
                f"score: {composite_score} Breakdown: {sub_scores}"
            )

        # Sort templates by score descending
        scored_templates.sort(key=lambda t: t.score, reverse=True)

        # Manual Override handling
        if override_template_id:
            override_match = next(
                (t for t in scored_templates if t.template_id.lower() == override_template_id.lower() or Path(t.template_id).stem.lower() == override_template_id.lower()),
                None,
            )
            if override_match:
                logger.info(f"[CompatibilityEngine] Manual override active. Forcing template '{override_match.template_id}'.")
                alts = [
                    {"template_id": t.template_id, "score": t.score}
                    for t in scored_templates
                    if t.template_id != override_match.template_id
                ]
                return SelectionResult(
                    selected_template_id=override_match.template_id,
                    selected_template_data=override_match.template_data,
                    score=1.0,  # Override score indicator
                    alternatives=alts,
                    analysis=analysis.to_dict(),
                )
            else:
                logger.warning(
                    f"[CompatibilityEngine] Requested manual override '{override_template_id}' not found in available templates. Falling back to automatic selection."
                )

        winning_template = scored_templates[0]

        # Check minimum score threshold
        if winning_template.score < min_score_threshold:
            rec = CompatibilityEngine._build_surface_recommendation(analysis)
            msg = (
                f"Mockup surface not found! Top template '{winning_template.template_id}' achieved score {winning_template.score:.2f}, "
                f"which is below minimum compatibility threshold ({min_score_threshold}). "
                f"Please add a mockup template matching surface recommendation: product_color={rec['recommended_product_colors']}, "
                f"contrast_profile='{rec['recommended_contrast_profile']}'."
            )
            logger.error(f"[CompatibilityEngine] {msg}")
            raise NoCompatibleTemplateFoundError(
                msg,
                clipart_analysis=analysis,
                required_surface_recommendation=rec,
            )

        alts = [
            {"template_id": t.template_id, "score": t.score}
            for t in scored_templates[1:]
        ]

        logger.info(
            f"[CompatibilityEngine] Winner selected: '{winning_template.template_id}' "
            f"with score {winning_template.score:.3f} (Product: {winning_template.metadata.product_color})"
        )

        return SelectionResult(
            selected_template_id=winning_template.template_id,
            selected_template_data=winning_template.template_data,
            score=winning_template.score,
            alternatives=alts,
            analysis=analysis.to_dict(),
        )

    @staticmethod
    def _calculate_sub_scores(
        art: ClipartAnalysis, t_meta: CompatibilityMetadata
    ) -> dict[str, float]:
        """Calculate weighted sub-scores between artwork metrics and template metadata."""
        # 1. Luminance Contrast Score (0.0 to 1.0)
        prod_lum = COLOR_LUMINANCE.get(t_meta.product_color.lower(), 0.50)
        lum_diff = abs(art.average_brightness - prod_lum)
        # Higher luminance difference = higher contrast = better score
        contrast_score = min(1.0, lum_diff / 0.70)

        # Penalize hard collisions (e.g. dark text art brightness < 0.35 on dark shirt lum < 0.30)
        if art.brightness_category == "dark" and prod_lum < 0.35:
            contrast_score = 0.05
        elif art.brightness_category == "light" and prod_lum > 0.75:
            contrast_score = 0.10

        # 2. Dominant Color Separation Score
        color_sep_score = 1.0
        # Check if product color matches preferred colors
        if t_meta.product_color in art.preferred_product_colors:
            color_sep_score = 1.0
        else:
            # Partial penalty if product color is not preferred
            color_sep_score = 0.40

        # 3. Brightness Compatibility Score
        if art.brightness_category in t_meta.compatible_brightness:
            brightness_score = 1.0
        else:
            brightness_score = 0.20

        # 4. Saturation Compatibility Score
        if art.saturation_category in t_meta.compatible_saturation:
            saturation_score = 1.0
        else:
            saturation_score = 0.50

        # 5. Aspect Ratio & Fit
        aspect_score = 0.85  # Standard default fit score

        # 6. Background Complexity Fit
        if art.complexity_category == "detailed" and t_meta.background_tone in ("neutral", "light"):
            complexity_score = 1.0
        elif art.complexity_category == "minimal" and t_meta.background_tone == "textured":
            complexity_score = 0.90
        else:
            complexity_score = 0.75

        return {
            "contrast": round(contrast_score, 3),
            "color_separation": round(color_sep_score, 3),
            "brightness": round(brightness_score, 3),
            "saturation": round(saturation_score, 3),
            "aspect": round(aspect_score, 3),
            "complexity": round(complexity_score, 3),
        }

    @staticmethod
    def _build_surface_recommendation(art: ClipartAnalysis) -> dict[str, Any]:
        """Construct actionable recommendation for missing mockup surface."""
        return {
            "clipart_brightness": art.brightness_category,
            "clipart_average_brightness": art.average_brightness,
            "clipart_dominant_colors": art.dominant_colors,
            "recommended_product_colors": art.preferred_product_colors,
            "recommended_contrast_profile": "light_or_pastel_art" if art.brightness_category == "light" else "dark_or_colorful_art",
            "suggested_product_types": ["tshirt", "sweatshirt", "mug"],
        }
