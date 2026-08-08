# Lifestyle Mockup Smart Generation — Implementation Plan v2

## Problem Statement

When a theme has 100+ clipart images, lifestyle mockup generation must:
1. Sample the right representative character images (not props/patterns).
2. Classify the theme's visual profile into one of 4 groups.
3. Lookup matching surfaces via O(1) bucket — not runtime scoring.
4. Render 4–10 mockups. If fewer than 6 → still render AND log the gap to DB so missing
   surfaces can be generated and a re-run triggered.
5. Be fully modular: any shop can enable lifestyle via config, and future layout types
   (wall art multi-clipart) can be added without touching core rendering code.

---

## Confirmed Design Decisions

| Decision | Answer |
|---|---|
| Surface in multiple groups? | **YES** — a surface can belong to multiple groups |
| Min mockups per listing | **6** |
| Max mockups to render | **10** |
| Coverage failure behavior | **Render whatever is available (4–5) AND log gap to DB. No full abort.** |
| Asset source for lifestyle | **Upscaled 4K images from Google Drive `main_data/`** (not `no_bg`) |
| Lifestyle scope | **Any shop can enable it via shop_config.yaml** (not just Shop 2) |

---

## Architecture: Modular Layout Strategy Pattern

The most important SDE3 insight here is that lifestyle mockup rendering has two distinct
**layout modes**, and more may come:

1. **`SingleProductLayout`** (current): One representative clipart → one surface → one JPEG.
2. **`WallArtLayout`** (future): Multiple clipart items arranged in a grid on one surface → one JPEG.

These are fundamentally different rendering contracts. The correct design is a **Strategy Pattern**:

```
LifestyleOrchestrator
        │
        ├── SurfaceGroupIndex (O(1) bucket lookup)
        ├── ThemeClassifier (classify → group)
        └── LifestyleLayoutStrategy (abstract)
                ├── SingleProductLayout (renders 1 clipart per surface)
                └── WallArtLayout (renders N cliparts per surface — future)
```

Each product entry in `shop_config.yaml` declares which layout strategy to use:

```yaml
lifestyle:
  enabled: true
  products:
    - name: black_t-shirt_1
      layout: single_product        # current mode
    - name: wallart_1
      layout: wall_art              # future mode — multiple cliparts on one surface
      wall_art_count: 6             # how many clipart items per wall art surface
```

---

## Phase 1: Clarification — Folder Structure & How `metadata.json` is Populated

### 📁 Standard Lifestyle Product Template Folder Structure

```
lifestyle_products/
└── <surface_folder_name>/           <-- e.g. black_t-shirt_1, mug_1, white_tshirt_1
    ├── blank.png                    <-- Clean high-res blank photo (e.g. 4000x4000)
    ├── mask.png                     <-- Print area mask (white = print region, black = background)
    ├── shadow_overlay.png           <-- Grayscale shadow/wrinkle overlay
    ├── config.json                  <-- Perspective corners & composition settings
    ├── metadata.json                <-- Surface metadata & compatibility groups
    ├── preview.png                  <-- (Optional) Preview rendering
    └── thumbnail.png                <-- (Optional) Surface thumbnail
```

---

### 📄 Clarification: `product_color` & `metadata.json` Generation

Our script (`scripts/assign_surface_groups.py`) automatically infers the color from the folder name:
- `black_t-shirt_1` $\to$ `product_color: "black"` $\to$ `compatibility_groups: ["light_art", "colorful_art", "medium_art"]`
- `white_tshirt_1` $\to$ `product_color: "white"` $\to$ `compatibility_groups: ["dark_art", "colorful_art", "medium_art"]`
- `brown_tshirt_1` $\to$ `product_color: "brown"` $\to$ `compatibility_groups: ["dark_art", "medium_art"]`
- `mug_1` $\to$ `product_color: "white"` $\to$ `compatibility_groups: ["dark_art", "colorful_art", "medium_art"]`

#### Updated `metadata.json` Schema:
```json
{
  "template_name": "Black T-Shirt Lifestyle",
  "category": "Shirt",
  "product_type": "tshirt",
  "product_color": "black",
  "compatibility_groups": ["light_art", "colorful_art", "medium_art"],
  "resolution": [4000, 4000],
  "version": "1.0"
}
```

---

## Phase 2: Character Image Sampling Strategy

Sampling is **filename-pattern based** (naming convention: `THEME_CATEGORY_NNN.png`).

**Priority order (descending):**
```
1. MAIN_CHARACTER images    → e.g., baby_MAIN_CHARACTER_001.png, baby_MAIN_CHARACTER_002.png
2. SUB_CHARACTER images     → e.g., baby_SUB_CHARACTER_001.png
3. GROUP_CHARACTER images   → e.g., baby_GROUP_CHARACTER_001.png
4. Other *CHARACTER* images → any filename containing "CHARACTER" (case insensitive)
5. Fallback                 → any PNG in asset_dir that is not PROP, PATTERN, BACKGROUND
```

**Skip always:** filenames containing `PROP`, `PATTERN`, `BACKGROUND`, `BORDER`, `ELEMENT`.
**Cap:** Maximum 10 images total.

---

## Phase 3: Theme Visual Classification

After collecting 10 images, run **batch analysis** on all of them:
- Analyze each using existing `ClipartAnalyzer.analyze_clipart()`.
- Average `average_brightness` and `saturation` values across all 10.
- Classify into ONE group:

```python
if avg_brightness < 0.35:
    theme_group = "dark_art"
elif avg_brightness > 0.70:
    theme_group = "light_art"
elif avg_saturation > 0.65:
    theme_group = "colorful_art"
else:
    theme_group = "medium_art"
```

---

## Phase 4: Surface Bucket Lookup + Render

```
theme_group = "colorful_art"
        │
SurfaceGroupIndex.get_surfaces_for_group("colorful_art")
        │
→ ["black_t-shirt_1", "brown_tshirt_1", "mug_2", "pillow_2", "wallart_2", ...]
        │
Cap at MAX=10
        │
Render each → LifestyleLayoutStrategy.render()
        │
JPEG Quality 93 + PNG
```

**Coverage gap handling (render available + DB log):**
```python
if len(surfaces) < MIN_MOCKUPS (6):
    logger.warning(f"[Lifestyle] Only {len(surfaces)} surfaces for group '{theme_group}'. Minimum is 6. Rendering available and logging gap.")
    write_coverage_gap_to_db(...)
# Renders available surfaces (4-5) anyway!
```

---

## Implementation Steps

1. `exceptions.py` — Add `InsufficientMockupCoverageError` and `MissingSurfaceGroupError`.
2. `shop_config.py` — Add `layout` field to `LifestyleProductConfig`.
3. `scripts/assign_surface_groups.py` — Script to auto-assign groups from `product_color` / folder name.
4. Run `assign_surface_groups.py` → updates all 13 `metadata.json` files in `lifestyle_products/`.
5. `surface_group_index.py` — Group index builder.
6. `theme_classifier.py` — Batch analysis + group decision.
7. Layout Strategies (`base_layout.py`, `single_product_layout.py`, `wall_art_layout.py` stub).
8. `lifestyle_orchestrator.py` — Core orchestration loop.
9. `orchestrator.py` — Wire `LifestyleOrchestrator.run()`.
10. `mockup_worker.py` — Catch error, write DB gap log.
11. `shop2_luna_cliparts/shop_config.yaml` — Add `layout` field to products.
12. `tests/test_lifestyle_orchestrator.py` — Unit tests.
13. Run full test suite.
