# Plan: Fix Silent Drive Upload Failure in Upscaling Stage

**Date:** 2026-07-30
**Status:** done
**Related:** [etsy_pipeline/workers/doc/new_features/implementation_plan_vm_first_storage_and_cleanup.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/new_features/implementation_plan_vm_first_storage_and_cleanup.md)

---

## Problem
The upscaling stage showed "completed" in the UI but images never appeared in Google Drive. Drive auth worked (folder creation succeeded), but individual PNG file uploads failed silently. In `GoogleDriveService.upload_folder_to_path()`, each file failure was caught with `logger.error()` + `continue`. When all files failed, the method returned `[]` with no exception, so `_upload_to_google_drive()` reported "Drive delivery complete" and then immediately purged the local `upscaled/` directory — permanently losing all upscaled images.

---

## Approach
Two surgical changes:

1. **`google_drive.py` — `upload_folder_to_path`**: After processing all files, raise `RuntimeError` if `success == 0` and there were files to upload. Track `failed_files` list for diagnostic logging. Log a `WARNING` for partial failures.

2. **`upscale_worker.py` — `_upload_to_google_drive`**: Capture the return value of `upload_folder_to_path` and log the count of uploaded files for observability. The existing `except` block re-raises as `UpscalingError`, keeping local upscaled files on disk.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/services/google_drive.py` — Fixed `upload_folder_to_path` to raise `RuntimeError` when all uploads fail, and restored accidental `raise RuntimeError` removal in `_get_or_create_folder_by_path`.
- `etsy_pipeline/workers/upscale_worker.py` — Capture and log `uploaded_ids` count from `upload_folder_to_path`.

**Out of scope:** Drive credential/auth issues, partial upload retry logic.

---

## Steps
1. Fix `upload_folder_to_path` in `google_drive.py`. ✅
2. Update `_upload_to_google_drive` in `upscale_worker.py`. ✅
3. Run `ruff check` — All checks passed. ✅
4. Document in `bug_resolvers/`. ✅

---

## Rollback
Revert edits to `etsy_pipeline/services/google_drive.py` and `etsy_pipeline/workers/upscale_worker.py`.
