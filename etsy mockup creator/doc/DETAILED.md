# 🔬 Etsy Mockup Creator — Detailed Module Specification

This document contains a comprehensive, module-by-module technical specification of all packages, classes, scripts, and endpoints within `etsy mockup creator`.

---

## 📂 1. `rendering/` Package — Multi-Shop & Business Logic

### `rendering/plugins/`
- **`orchestrator.py` (`RenderingOrchestrator`):**
  - Central dispatcher that reads `shop_config.yaml` and routes execution to `HeroPlugin` and `LifestyleOrchestrator`.
  - Accepts both `asset_dir` (700px `no_bg`) and optional `upscaled_asset_dir` (4K `upscaled`).

- **`hero_plugin.py` (`HeroPlugin`):**
  - Executes standard JSON template canvas rendering via CLI subprocess (`src.main`).
  - Saves high-quality JPEG (`quality=93`) + PNG mockups.

- **`lifestyle_plugin.py` (`LifestylePlugin`):**
  - Core photorealistic photo compositing engine.
  - Fits RGBA artwork into perspective quad (`_warp_perspective_rgba`), multiplies normalized shadow overlay (`ImageChops.multiply`), composites onto `blank.png`, and exports JPEG (`quality=93`, `optimize=True`).

- **`lifestyle_orchestrator.py` (`LifestyleOrchestrator`):**
  - Smart orchestrator for lifestyle mockups.
  - Samples priority character images (`ThemeClassifier`), classifies theme group, performs O(1) bucket lookup (`SurfaceGroupIndex`), checks minimum surface coverage (6 surfaces), logs DB gap metrics if coverage is low, and dispatches layout strategy.

- **`layout_strategies/`:**
  - **`base_layout.py` (`LifestyleLayoutStrategy`):** Abstract Strategy interface.
  - **`single_product_layout.py` (`SingleProductLayout`):** Renders single clipart onto lifestyle surface.
  - **`wall_art_layout.py` (`WallArtLayout`):** Strategy stub for future multi-clipart wall art grid rendering.

---

### `rendering/compatibility/`
- **`surface_group_index.py` (`SurfaceGroupIndex`):**
  - Scans `lifestyle_products/*/metadata.json` and builds an in-memory `dict[str, list[str]]` mapping groups (`dark_art`, `light_art`, `colorful_art`, `medium_art`) to surface names.

- **`theme_classifier.py` (`ThemeClassifier`):**
  - Samples up to 10 character PNGs using naming hierarchy:
    `MAIN_CHARACTER` $\to$ `SUB_CHARACTER` $\to$ `GROUP_CHARACTER` $\to$ fallback.
  - Computes mean brightness and saturation to classify theme into one group.

- **`clipart_analyzer.py` (`ClipartAnalyzer`):**
  - Extracts non-transparent RGBA pixels and computes perceived luminance, saturation, color temperature, visual complexity, and dominant colors.

- **`compatibility_engine.py` (`CompatibilityEngine`):**
  - Deterministic scoring engine that calculates composite compatibility score $S \in [0.0, 1.0]$.
  - Raises `NoCompatibleTemplateFoundError` with explicit surface recommendations when min threshold ($0.50$) is not met.

- **`template_schema.py` (`CompatibilityMetadata`):**
  - Pydantic schema validator for JSON template metadata.
  - Raises `MissingTemplateMetadataError` if `"compatibility_metadata"` block is absent.

- **`metadata_generator.py` (`auto_generate_metadata`):**
  - Utility to auto-generate and attach `"compatibility_metadata"` JSON blocks to standard hero template files.

---

### `rendering/config/`
- **`shop_config.py` (`ShopConfig`, `LifestyleConfig`, `LifestyleItemConfig`):**
  - Pydantic models for loading and validating `shop_config.yaml` files across all shops.

---

## 🛠️ 2. `src/` Package — Core Canvas & Graphics Engine

- **`main.py`:** CLI entry point (`python -m src.main`). Accepts `--theme`, `--output`, `--templates`, `--template-override`, `--upscaled-dir`.
- **`generator.py` (`Generator`):** Batch orchestrator. Integrates `ClipartAnalyzer` and `CompatibilityEngine` before rendering canvas templates.
- **`renderer.py` (`Renderer`):** Layer composition engine. Iterates JSON elements array and draws images, text placeholders, backgrounds, and drop shadows onto PIL canvas.
- **`effects.py`:** Image manipulation utilities — aspect-fit scaling, soft blurred drop shadows, outline border dilation.
- **`text_renderer.py`:** Google Fonts typography engine. Manages Outfit font loading, text wrapping, and anchor alignment.
- **`image_loader.py`:** Crawls theme subfolders (`character`, `combo`, `prop`, `pattern`, `scene`) and indexes transparent PNGs.

---

## 📄 3. `templates/` Directory — Standard JSON Specifications

Standard hero JSON templates define canvas elements:
```json
{
  "name": "White T-Shirt Flatlay",
  "canvas_size": [2000, 2000],
  "compatibility_metadata": {
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
  },
  "elements": [
    {
      "type": "image",
      "x": 1000,
      "y": 1000,
      "width": 400,
      "height": 400,
      "anchor": "center",
      "source": { "category": "character", "index": 0 }
    }
  ]
}
```

---

## 🌐 4. `web_editor/` Directory — Flask Server & Template Editor UI

- **`server.py`:** Flask API server.
  - `/api/compatibility/analyze` (POST) — Clipart analysis & template ranking endpoint.
  - `/api/batch-generate` (POST) — Triggers batch mockup generation.
  - `/api/render-template` (POST) — Live canvas rendering endpoint for web UI.
- **`index.html` & `static/`:** Visual drag-and-drop web editor UI. Allows users to interactively position elements, edit text properties, adjust drop shadows, and preview mockups live.
