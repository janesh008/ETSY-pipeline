# Plan: Upscale Direct-to-Drive Storage & Drive API Verification

**Date:** 2026-07-29  
**Status:** approved  
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md), [`etsy_pipeline/workers/doc/new_features/implementation_plan_vm_first_storage_and_cleanup.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/new_features/implementation_plan_vm_first_storage_and_cleanup.md)

---

## Problem
1. Stage 3 (AI Upscaling) outputs were not appearing in Google Drive because `_upload_to_google_drive()` silently skipped upload when Drive service was unconfigured or failing, followed by an immediate local disk purge (`shutil.rmtree(upscaled_dir)`).
2. Upscaled images were missing from stage completion checks (`_is_stage_100pct_complete`), causing Stage 3 to restart from scratch every time.

---

## Approach
1. **Google Drive API Verification**:
   - In `GoogleDriveService` (`etsy_pipeline/services/google_drive.py`):
     - Add `find_folder_id_by_path(parent_id, path_parts)`: Resolve path without creating missing folders.
     - Add `list_files_in_folder(folder_id)`: List all non-trashed files in a Google Drive folder.
   - In `PipelineRunnerService._is_stage_100pct_complete()`:
     - Check Google Drive path `Clipart/main_data/<date_folder>/<theme_slug>/`.
     - If count of PNGs in Google Drive $\ge$ `job.total_prompt_count`, mark Stage 3 `Completed ✅` and skip worker.
2. **Safe Drive Upload & File Cleanup**:
   - In `UpscaleWorker` (`etsy_pipeline/workers/upscale_worker.py`):
     - Upload upscaled PNGs to Google Drive path `Clipart/main_data/<date_folder>/<theme_slug>/`.
     - Raise `UpscalingError` if Drive upload fails so local files are **retained** on disk instead of being purged.
     - Purge local `upscaled/` directory only after Google Drive upload succeeds.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/services/google_drive.py` — Add `find_folder_id_by_path` and `list_files_in_folder`.
- `craftdesk_api/services/pipeline_runner.py` — Update `_is_stage_100pct_complete()` to verify Stage 3 via Google Drive API.
- `etsy_pipeline/workers/upscale_worker.py` — Enforce safe Drive upload and conditional disk purge.

---

## Steps
1. Add `find_folder_id_by_path` and `list_files_in_folder` in `etsy_pipeline/services/google_drive.py`.
2. Update `_is_stage_100pct_complete()` for `upscaling` in `craftdesk_api/services/pipeline_runner.py`.
3. Update `_upload_to_google_drive()` and local purge condition in `etsy_pipeline/workers/upscale_worker.py`.
4. Update documentation in `etsy_pipeline/workers/doc/DETAILED.md` and `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`.
5. Format code, test, and rebuild graph (`python scripts/build_graph.py`).
