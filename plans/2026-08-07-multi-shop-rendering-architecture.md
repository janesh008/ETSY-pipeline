# Plan: Multi-Shop Rendering Architecture

**Date:** 2026-08-07  
**Status:** approved — implementation in progress  
**Author:** Antigravity

---

## Problem Statement

One asset generation pipeline (Prompt → Image → BgRemoval → Upscale) serving three Etsy shops.
Each shop needs different mockup styles, metadata, and PDF. Currently only Shop 1 (pixelbarstudio) is served.
The existing hero mockup creator must remain untouched.

## Decisions Made

- Lifestyle blank images: **Git** (inside `rendering/lifestyle_products/`)
- LunaClipArts products: mug, tshirt, tshirt_girl, tshirt_boy_stylish, tshirt_girl_stylish, tshirt_back, tshirt_baby_boy, wall_art, portrait
- Multi-shop pipeline: **selectable per run** (UI picker lets user choose which shops to include)

## Approach

Configuration-driven, plugin-based rendering system inside `etsy mockup creator/rendering/`.
Each shop is a self-contained folder. Adding a new shop = one new folder + config YAML. Zero code changes.
Two pipeline profiles: `single_shop` (original, unchanged) and `multi_shop` (new).

## Rejected Alternatives

- Three separate pipelines: rejected (duplicates code, hard to maintain)
- PdfPlugin: rejected (existing PDF generation stays untouched)
- Service account for Google Drive: rejected (personal Drive doesn't support SA uploads; OAuth token approach used instead)

## Files Created / Modified

### New Files
- `etsy mockup creator/rendering/` — full rendering system
- `etsy mockup creator/rendering/HOW_TO_ADD_NEW_SHOP.md`
- `etsy mockup creator/rendering/shops/shop1_pixelbarstudio/` (templates moved here)
- `etsy mockup creator/rendering/shops/shop2_luna_cliparts/`
- `etsy mockup creator/rendering/shops/shop3_crisp_png_co/`
- `etsy mockup creator/rendering/lifestyle_products/` (9 product folders)
- `etsy mockup creator/rendering/plugins/` (base_plugin, hero_plugin, lifestyle_plugin, orchestrator)
- `etsy_pipeline/config/pipeline_profiles.yaml`

### Modified Files
- `etsy_pipeline/workers/mockup_worker.py` — templates path updated to shop1 new location
- `etsy_pipeline/models/job.py` — add `shop_ids`, `pipeline_profile` fields
- `craftdesk_web` publish page — shop variant selector UI

### Frozen (Never Touch)
- `etsy mockup creator/src/*.py` — all 5 files
- `etsy mockup creator/assets/`
- `MockupWorker._create_clickable_folder_pdf()`

## Milestones

- [x] M1: Folder scaffold + templates move + MockupWorker path update
- [ ] M2: Shop config loader (Pydantic) + HeroPlugin subprocess wrapper
- [ ] M3: Shop 2 hero template JSON + test
- [ ] M4: Shop 3 hero templates + pipeline profiles YAML + UI pipeline picker
- [ ] M5: SEO metadata prompts for Shop 2 + Shop 3 + MetadataWorker shop-aware
- [ ] M6: GCS/Drive per-shop output folder structure
- [ ] M7: Publish page shop variant selector UI
- [ ] M8: LifestylePlugin: tshirt + mug + 7 more product templates for Shop 2 + Shop 3
