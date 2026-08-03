# Implementation Plan — Fix Etsy Listing AI/Renewal Parameters, Mockup Uploads, and Clipart PNG Count

Date: 2026-08-03  
Branch: `feat/batch-pipeline-background-widget`  

---

## Problem Statement

1. **Etsy Listing Creation & Mockup Upload Issue**:
   - `is_ai_created` (`True`) and `renewal_option` (`"automatic"`) are present in `listing.json` but were not extracted or passed from `GcsListingRequest` / `publish_from_gcs` when creating draft listings on Etsy.
   - When publishing from GCS, if `gcs_prefix` contained `/mockups/` (e.g. `"Clipart/2026-08-02/Chubby_Spiderman/mockups/"`), the code constructed `f"{gcs_prefix}/mockups/"`, resulting in `"/mockups/mockups/"`. This returned zero mockups, causing mockup image downloads and uploads to fail.

2. **PNG Count Calculation (146 vs 73)**:
   - `ImageLoader.load_theme_images()` traversed all subdirectories under the theme output folder, including both `raw_images` (73 PNGs) and `no_bg` (73 PNGs), finding 146 total PNG files.
   - This caused hero mockups to render `{bundle_count}` as `146` ("146 Premium PNGs"), leading Gemini Vision to output `"Included Files: 146 high-resolution PNG images"` in the Etsy listing description when only 73 transparent PNGs exist in `no_bg`.

---

## Proposed Changes

### 1. Mockup Image Loader (`etsy mockup creator/src/image_loader.py`)

- Update `load_theme_images(theme_dir)`:
  - If `theme_dir` contains a `no_bg` directory, automatically switch `theme_dir` to `no_bg`.
  - In `os.walk(theme_dir)`, ignore any paths containing `raw_images`, `raw_data`, `mockups`, `upscaled`, or `pdf`.
  - Ensure image counts (`{bundle_count}`) strictly reflect transparent PNGs in `no_bg` (73 PNGs).

### 2. Etsy API Schemas & Service (`craftdesk_api`)

#### [MODIFY] [craftdesk_api/schemas/etsy.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/etsy.py)
- Add optional `is_ai_created: bool | None = None` and `renewal_option: str | None = None` fields to `GcsListingRequest`.

#### [MODIFY] [craftdesk_api/routers/etsy.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/etsy.py)
- Forward `is_ai_created` and `renewal_option` from `body` into `EtsyListingService.publish_from_gcs()`.

#### [MODIFY] [craftdesk_api/services/etsy_listing_service.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_listing_service.py)
- Update `publish_from_gcs()` to:
  1. Sanitize `gcs_prefix` (strip `/mockups` or `/mockups/` if present) to construct clean `mockup_prefix` (`Clipart/.../mockups/`) and `pdf_prefix` (`Clipart/.../`).
  2. Extract `is_ai_created` and `renewal_option` from `record` or request overrides.
  3. Pass `is_ai_created` and `renewal_option` to `_create_etsy_listing()`.

---

## Verification Plan

### Automated Tests
- Run full pytest test suite:
  `python -m pytest craftdesk_api/tests/ tests/`

### Manual Verification
- Test `load_theme_images` against theme directories containing `raw_images` and `no_bg` to verify only `no_bg` files are counted.
- Verify `publish_from_gcs` prefix resolution logic for prefixes with or without trailing `/mockups/`.
