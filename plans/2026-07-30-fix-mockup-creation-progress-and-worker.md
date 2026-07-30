# Plan: Fix Mockup Creation Worker Execution and Progress Tracking

**Date:** 2026-07-30
**Status:** approved
**Related:** [craftdesk_api/doc/PIPELINE_ARCHITECTURE.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)

---

## Problem
The `mockup_creation` stage was failing or remaining stuck at `Status: pending. Progress: 0%. Elapsed: 0s`. This occurred due to an `AttributeError` in the stage monitoring loop (`st_res.error` instead of `st_res.error_message`), static progress reporting in `MockupWorker`, incomplete Google Drive fallback paths (`main_data` vs `raw_data`), and hardcoded Google Drive folder IDs.

---

## Approach
1. Fix `st_res.error` to `st_res.error_message` (or `getattr(st_res, "error_message", None)`) in `craftdesk_api/services/pipeline_runner.py`.
2. Enhance `pipeline_runner.py` monitoring loop to check generated file counts in `output/.../mockups` and dynamically update progress between 10% and 90% while `MockupWorker` runs.
3. Update `MockupWorker` in `etsy_pipeline/workers/mockup_worker.py`:
   - Include fallback search in `Clipart/main_data/<date_folder>/<theme_slug>` on Google Drive and GCS to locate upscaled images if local `no_bg` is missing.
   - Use `self._settings.google_drive_folder_id or ETSY_DRIVE_FOLDER_ID` consistently.
   - Gracefully handle `_find_first_image` to find available input images safely.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/pipeline_runner.py` — Fix `AttributeError` on line 574 and add dynamic progress calculation for `mockup_creation`.
- `etsy_pipeline/workers/mockup_worker.py` — Add fallback for `main_data` upscale input images, use dynamic parent drive folder ID, and update progress safely.

**Out of scope:**
- Modifying `etsy mockup creator` internal rendering engine scripts.

---

## Risks & edge cases
- *Edge case:* Local `no_bg` directory is empty, but Google Drive contains upscaled images in `main_data`.
  *Mitigation:* Add fallback in `MockupWorker` to pull upscaled images from `main_data` if `no_bg` and `raw_images` local/GCS/Drive checks are empty.

---

## Steps
1. Modify `craftdesk_api/services/pipeline_runner.py` to fix `st_res.error` to `st_res.error_message` and enable dynamic progress updating for mockup creation.
2. Modify `etsy_pipeline/workers/mockup_worker.py` to handle input fallbacks, parent drive folder resolution, and smooth step progress.
3. Run tests and lint checks (`ruff check .`, `mypy etsy_pipeline`, `pytest`).
4. Update living documentation in `craftdesk_api/doc/` and `etsy_pipeline/workers/doc/`.
