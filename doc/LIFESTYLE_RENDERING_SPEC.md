# Lifestyle Mockup Rendering Pipeline Specification

## Pure RGBA Compositing Contract

The `LifestylePlugin` ([lifestyle_plugin.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/rendering/plugins/lifestyle_plugin.py)) executes a strict 5-stage RGBA compositing pipeline to render transparent PNG artwork onto real photo mockups (e.g. T-shirts, mugs, wall art).

### Pipeline Stages & Debug Outputs

1. **Stage 1 — Artwork RGBA Collage (`01_artwork_rgba.png`)**
   - Loads transparent PNG clipart assets.
   - Builds grid/collage preserving original RGBA alpha transparency.
   - Never converts transparent artwork to RGB.

2. **Stage 2 — Perspective Transform (`02_perspective_artwork.png`)**
   - Applies 4-point perspective warp matrix (`cv2.getPerspectiveTransform`) on the 4-channel RGBA numpy array.
   - `cv2.warpPerspective` uses `borderMode=cv2.BORDER_CONSTANT` with `borderValue=(0,0,0,0)` to maintain complete transparency outside the print region.

3. **Stage 3 — Mask Clipping (`03_masked_artwork.png`)**
   - Applies `mask.png` as a clipping mask using `ImageChops.multiply(artwork_alpha, mask_grayscale)`.
   - Does **NOT** fill transparent artwork areas with black. Mask restricts alpha visibility ONLY.

4. **Stage 4 — Print Layer Fabric Shading (`04_shadow_applied_artwork.png`)**
   - Normalizes `shadow_overlay.png` luminance so the maximum brightness in the print quad is 255.
   - Multiplies artwork RGB by normalized shadow overlay RGB using `ImageChops.multiply(art_rgb, shd_norm_rgb)`.
   - Blends by `shadow_opacity` (`0.75` default).
   - Re-attaches the clipped alpha channel `(R, G, B, Alpha)`.
   - Shading affects **ONLY** printed artwork pixels, leaving the surrounding photo untouched.

5. **Stage 5 — Alpha Composition (`05_final.png`)**
   - Performs `Image.alpha_composite(blank_photo_rgba, print_layer_rgba)`.
   - Preserves 100% of `blank.png` outside the artwork bounds (model, face, hair, jeans, background, lighting).

---

## Verification & Debug Outputs

When testing with `scripts/test_lifestyle_mockup.py`:
- `01_artwork_rgba.png`: Raw RGBA collage on transparent canvas.
- `02_perspective_artwork.png`: Perspective warped artwork with zero edge halos.
- `03_masked_artwork.png`: Clipped artwork with zero black background fill.
- `04_shadow_applied_artwork.png`: Fabric shaded artwork.
- `05_final.png` / `<product_name>.png`: Complete photorealistic lifestyle mockup output.
