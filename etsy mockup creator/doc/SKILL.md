# 🛠️ Etsy Mockup Creator — Engineering Skill & Architecture Rules

This document outlines the core technical conventions, architecture patterns, and gotchas for developers and AI agents modifying `etsy mockup creator`.

---

## 🏛️ Key Architectural Principles

### 1. Strategy Pattern Layouts (`rendering/plugins/layout_strategies/`)
- All lifestyle product renderings use the Strategy Pattern (`LifestyleLayoutStrategy`).
- Current default: `SingleProductLayout` (prints single character on surface).
- Future extension: `WallArtLayout` (arranges multiple clipart items in a grid on wall art surfaces).
- **Rule:** Never hardcode rendering logic inside `LifestyleOrchestrator` — dispatch via `Strategy.render()`.

### 2. O(1) Surface Bucket Indexing (`SurfaceGroupIndex`)
- Surfaces are pre-indexed into 4 visual compatibility groups:
  `dark_art`, `light_art`, `colorful_art`, `medium_art`.
- Surface groups are declared in `lifestyle_products/*/metadata.json`.
- **Rule:** Never perform runtime N×M scoring loops over surfaces. Always use `SurfaceGroupIndex.get_surfaces_for_group(group)`.

### 3. Strict Exception Handling (Zero Fallbacks / No Dummy Data)
- **Rule:** If a template JSON is missing `"compatibility_metadata"`, raise `MissingTemplateMetadataError`.
- **Rule:** If a lifestyle surface `metadata.json` is missing `"compatibility_groups"`, raise `MissingSurfaceGroupError`.
- Never insert fallback default values or dummy data when required schema blocks are missing.

---

## 🎨 Image Compositing & Pipeline Rules

### 1. Pure RGBA Alpha Preservation
- Clipart artwork must maintain transparency throughout the entire rendering pipeline.
- **Rule:** Never convert transparent RGBA artwork to RGB before compositing.
- Alpha channel masking:
  ```python
  # Apply fabric shading while preserving alpha channel
  final_rgb = Image.blend(art_rgb, ImageChops.multiply(art_rgb, normalized_shadow), opacity)
  final_rgba = Image.merge("RGBA", (*final_rgb.split(), art_alpha))
  ```

### 2. Perspective Warping (`_warp_perspective_rgba`)
- Uses OpenCV `cv2.getPerspectiveTransform` and `cv2.warpPerspective` with `borderValue=(0,0,0,0)`.
- Perspective corners in `config.json` can be absolute pixels `[x, y]` or percentage floats `(x <= 100.0)`.

### 3. File Size JPEG Export Optimization
- Saved output files:
  - Standard Hero Mockups $\to$ High-Quality JPEG (`quality=93`, `optimize=True`) + PNG.
  - Lifestyle Mockups $\to$ High-Quality JPEG (`quality=93`, `optimize=True`) + PNG.
- **Rule:** JPEGs must remain between **1.0 MB – 1.8 MB** for fast Etsy API batch publishing.

---

## ⚠️ Developer Gotchas

1. **Folder Names with Spaces:**
   - The directory name is `etsy mockup creator` (contains spaces).
   - In test files, always include path resolution before importing:
     ```python
     mockup_creator_dir = Path(__file__).resolve().parent.parent / "etsy mockup creator"
     sys.path.insert(0, str(mockup_creator_dir))
     ```

2. **Asset Directory Resolution:**
   - Standard Hero Canvas templates use `no_bg/` (700px) images for low RAM grid rendering.
   - Lifestyle Photo templates use `upscaled/` (4K 4096px from Drive `main_data/`) for photorealistic print detail.

3. **Updating Surface Metadata:**
   - Whenever you add a new surface folder under `lifestyle_products/`, run:
     ```powershell
     python scripts/assign_surface_groups.py
     ```
   - This automatically writes `metadata.json` with `product_color` and `compatibility_groups`.
