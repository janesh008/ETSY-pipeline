# Implementation Plan — Automatic Template Compatibility Selection

Extend the Etsy Mockup Creator pipeline with an automated visual compatibility selection layer. Given arbitrary transparent PNG clipart, the system analyzes visual attributes (dominant colors, brightness, saturation, contrast, visual complexity, aspect ratio) and deterministically ranks and selects the most visually compatible mockup template across categories (`tshirt`, `sweatshirt`, `tote_bag`, `mug`, `poster`, `pillow`) and surface tones (`light`, `dark`, `neutral`), while leaving the existing Gemini Canvas Template Factory intact.

---

## Key Principles & User Requirements

1. **Zero Clipart Modification:** Clipart artwork is NEVER altered (recolored or adjusted) to fit a template; templates are selected to adapt to the clipart's natural colors and brightness.
2. **Metadata Integration & Discovery:** Template compatibility metadata is embedded directly into template JSON files under a top-level `"compatibility_metadata"` key. An automated tool (`metadata_generator.py`) inspects new template background photos to auto-populate metadata.
3. **Strict Exception Handling (Zero Fallbacks):** If any template JSON is missing `"compatibility_metadata"`, the code raises `MissingTemplateMetadataError` detailing the exact file path and missing fields. No default fallbacks or dummy data are ever used.
4. **Missing Surface Error Guidance (`NoCompatibleTemplateFoundError`):** If no candidate template achieves a passing score (e.g. score $< 0.50$), the engine raises `NoCompatibleTemplateFoundError` specifying the analyzed clipart properties and detailing the required product surface parameters so the user can create and add the required template.
5. **Manual Override Support:** Supports explicit user override via CLI (`--template-override <id>`), API parameter (`template_override`), or Web Editor dropdown.
6. **Strict Logging:** Every module includes explicit `logger.info`, `logger.debug`, and `logger.error` statements for transparent troubleshooting.

---

## Proposed Changes

### Module 1: Clipart Visual Analysis Engine (`etsy mockup creator/rendering/compatibility/clipart_analyzer.py`)

#### [NEW] `clipart_analyzer.py`
- Implements `ClipartAnalyzer` class with `analyze_clipart(image_path_or_pil) -> ClipartAnalysis`.
- Extract non-transparent pixels (`alpha > 10`) from RGBA PNGs.
- Calculates:
  - `dominant_colors`: Top 3-5 dominant colors in Hex/RGB and HSL.
  - `average_brightness`: Perceived luminance ($0.299R + 0.587G + 0.114B$) of artwork pixels ($0.0 - 1.0$).
  - `color_temperature`: Warmth index based on Hue/Red-Blue ratio.
  - `saturation`: Mean S channel in HSL ($0.0 - 1.0$).
  - `contrast`: Standard deviation of luminance / RMS contrast ($0.0 - 1.0$).
  - `transparency`: Ratio of non-transparent pixels to total image bounding box area.
  - `visual_complexity`: Edge density score using Sobel filter / Canny gradient magnitude on non-transparent region.
  - `artwork_bbox`: `(min_x, min_y, max_x, max_y)` of non-transparent artwork.
  - `aspect_ratio`: Bounding box width / height ratio.
  - `estimated_print_area`: Bounding box area / total canvas area.
  - `preferred_product_colors`: Inferred compatible product surface color list (e.g. dark artwork $\to$ `["white", "cream", "light_grey"]`, light pastel artwork $\to$ `["black", "navy", "dark_charcoal"]`).

---

### Module 2: Template Metadata Schema & Auto-Generator (`etsy mockup creator/rendering/compatibility/template_schema.py` & `metadata_generator.py`)

#### [NEW] `template_schema.py` & `metadata_generator.py`
- Dataclass / Pydantic schema for template metadata:
```json
{
  "template_id": "tshirt_white_flatlay_01",
  "product_type": "tshirt",
  "product_color": "white",
  "background_tone": "neutral",
  "lighting": "soft",
  "print_area": "center_chest",
  "print_area_ratio": 0.55,
  "contrast_profile": "dark_or_colorful_art",
  "compatible_brightness": ["dark", "medium"],
  "compatible_saturation": ["medium", "high"]
}
```
- Includes helper tool `generate_template_metadata(template_json_path)` to auto-populate metadata when new templates are added.
- **Strict Exception Handling:** Raises `MissingTemplateMetadataError` if `"compatibility_metadata"` is missing or invalid.

---

### Module 3: Deterministic Compatibility Engine (`etsy mockup creator/rendering/compatibility/compatibility_engine.py`)

#### [NEW] `compatibility_engine.py`
- Implements `CompatibilityEngine` with `rank_templates(clipart_analysis, templates, min_score_threshold=0.50, override_template_id=None) -> SelectionResult`.
- Includes explicit `get_logger(__name__)` calls for all evaluation steps.
- Calculates composite score $S \in [0.0, 1.0]$ using weighted components:
  1. Luminance Contrast Score ($W=0.30$)
  2. Dominant Color Separation Score ($W=0.25$)
  3. Brightness Compatibility Score ($W=0.15$)
  4. Saturation Compatibility Score ($W=0.10$)
  5. Aspect Ratio & Print Area Fit ($W=0.10$)
  6. Background Complexity Fit ($W=0.10$)
- **Missing Surface Exception:** Raises `NoCompatibleTemplateFoundError` detailing missing surface parameters if no template scores above `min_score_threshold`.

---

### Module 4: Generator & CLI Integration (`etsy mockup creator/src/generator.py` & `src/main.py`)

#### [MODIFY] [generator.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/src/generator.py)
- Integrate compatibility selection step before template rendering loop.

#### [MODIFY] [main.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/src/main.py)
- Add `--template-override` CLI flag to force a specific template ID.

---

### Module 5: Web Editor Integration (`etsy mockup creator/web_editor/`)

#### [MODIFY] [server.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/web_editor/server.py)
- Add `/api/compatibility/analyze` endpoint.

#### [MODIFY] `web_editor/static/index.html` & `static/app.js`
- Add UI panel displaying Clipart Analysis, Recommended Template, Score, and Alternatives.

---

## Verification Plan

### Automated Tests
- Create `tests/test_clipart_analyzer.py` verifying pixel analysis math.
- Create `tests/test_compatibility_engine.py` covering all 9 clipart test cases:
  1. Dark monochrome clipart $\to$ Selects light/white surface template.
  2. Bright colorful clipart $\to$ Selects neutral/white surface template.
  3. Pastel clipart $\to$ Selects dark/charcoal surface template.
  4. Red-heavy clipart $\to$ Selects neutral/non-red surface template.
  5. Blue-heavy clipart $\to$ Selects warm/neutral surface template.
  6. Black artwork $\to$ Selects white/light surface template.
  7. White/light artwork $\to$ Selects dark/black surface template.
  8. Highly detailed artwork $\to$ Selects clean background template.
  9. Minimal artwork $\to$ Selects rich background template.
- Test `MissingTemplateMetadataError` when metadata is absent.
- Test `NoCompatibleTemplateFoundError` when no template reaches threshold.
- Run `python -m pytest tests/test_compatibility_engine.py`

### Manual Verification
- Test CLI selection and Web Editor UI panel.
