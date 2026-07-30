# Bug Resolver: Silent Drive Upload Failure in Upscaling Stage

## Problem Statement
The upscaling stage (Stage 3) showed "completed" in the CraftDesk UI but upscaled images never appeared in Google Drive. The Drive folder structure (`Clipart/main_data/<date>/<theme_slug>/`) was being created correctly, confirming Drive auth was valid, but the PNG files inside were never uploaded.

## Root Cause
In [GoogleDriveService.upload_folder_to_path](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/google_drive.py#L505-L567), individual file upload failures were silently swallowed:

```python
# BROKEN — exception caught and discarded
except Exception as e:
    logger.error(f"Failed to upload {file_path.name} ...")
    # no re-raise → method returns [] with no error
```

When all PNG uploads failed (e.g. Drive API permission issue on individual files), `upload_folder_to_path()` returned `[]` without raising. Back in `UpscaleWorker._upload_to_google_drive()`, no exception was seen, so:
1. "Google Drive delivery complete" was logged (false positive).
2. `shutil.rmtree(upscaled_dir)` ran and permanently deleted all local upscaled images.
3. Stage was marked `completed` in the UI.

## Fix Applied

### `etsy_pipeline/services/google_drive.py` — `upload_folder_to_path`
- Tracks `failed_files: list[str]`.
- After processing all files, **raises `RuntimeError`** if `success == 0` and there were files to upload, with diagnostic message listing failed filenames.
- Logs a `WARNING` for partial failures (some succeeded, some failed).
- Logs `INFO` with `success/total` count on completion.

### `etsy_pipeline/workers/upscale_worker.py` — `_upload_to_google_drive`
- Captures `uploaded_ids` return value and logs the exact count of files uploaded.
- The existing `except UpscalingError` block correctly prevents `shutil.rmtree()` from running when Drive upload fails.

## Failure Handling After Fix
- **All uploads fail** → `RuntimeError` → caught as `UpscalingError` → stage marked `failed` → local `upscaled/` kept on disk → user sees error in UI.
- **Partial failure** → warning logged, stage still completes with `success/total` count visible in logs.
- **All succeed** → normal "Drive delivery complete: N files uploaded" log.
