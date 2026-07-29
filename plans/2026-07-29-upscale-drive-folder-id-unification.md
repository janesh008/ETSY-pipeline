# Plan: Upscale Drive Folder ID Unification & Single Source of Truth

**Date:** 2026-07-29  
**Status:** approved  
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md), [`.env`](file:///d:/Janesh/ETSY/ETSY-pipeline/.env)

---

## Problem
1. `.env` configured `GOOGLE_DRIVE_FOLDER_ID=10LV99x6nFaBlEEGUiqVo1tyaYNv9e2ks`, whereas `upscale_worker_config.py` configured `ETSY_DRIVE_FOLDER_ID=1JWUBqtP-PG-hRLEQj4Kh_vNzfb_G_PCP` (the root `ETSY` folder). The backend completion check queried a different Drive parent folder than the worker uploaded to.
2. `_is_stage_100pct_complete(job, "upscaling")` had a local disk fallback check that caused false-positive stage skips whenever leftover files existed in `output/<date>/<theme>/upscaled/`, even when files were missing from Google Drive.

---

## Approach
1. **Update `.env`**: Set `GOOGLE_DRIVE_FOLDER_ID=1JWUBqtP-PG-hRLEQj4Kh_vNzfb_G_PCP`.
2. **Unify Drive Folder ID in `pipeline_runner.py`**:
   - Use `parent_id = settings.google_drive_folder_id or ETSY_DRIVE_FOLDER_ID` (`1JWUBqtP-PG-hRLEQj4Kh_vNzfb_G_PCP`).
3. **Google Drive Only Completion for Stage 3**:
   - For `stage_name == "upscaling"`, query Google Drive folder `Clipart/main_data/<date_folder>/<theme_slug>/`.
   - Remove local disk fallback check for Stage 3 so local leftovers cannot cause false-positive stage skips.

---

## Scope

**Files/modules touched:**
- `.env` — Update `GOOGLE_DRIVE_FOLDER_ID` to `1JWUBqtP-PG-hRLEQj4Kh_vNzfb_G_PCP`.
- `craftdesk_api/services/pipeline_runner.py` — Unify Drive parent folder ID and enforce Google Drive-only check for Stage 3 upscaling.

---

## Steps
1. Update `GOOGLE_DRIVE_FOLDER_ID` in `.env`.
2. Update `_is_stage_100pct_complete()` for `upscaling` in `craftdesk_api/services/pipeline_runner.py`.
3. Update `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`.
4. Format code, test, and rebuild graph (`python scripts/build_graph.py`).
