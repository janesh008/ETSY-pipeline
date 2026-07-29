# Plan: Google Drive Credential Path Resolution & Upscaling Stage Completion Fix

**Date:** 2026-07-29  
**Status:** approved  
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md), [`etsy_pipeline/services/google_drive.py`](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/google_drive.py)

---

## Problem
1. `GOOGLE_DRIVE_CLIENT_SEC_JSON=cred/client_secret.json` and `GOOGLE_DRIVE_TOKEN_JSON=cred/token.json` in `.env` are relative paths. When `craftdesk_api` or `uvicorn` runs from working directories outside the project root, `Path("cred/client_secret.json").exists()` evaluates to `False`, causing `GoogleDriveService` to fail to initialize with `ConfigurationError`.
2. In `_is_stage_100pct_complete(job, "upscaling")`, local VM `output/<date>/<theme>/upscaled/` was checked first. If leftover files existed locally from a previous partial run, it returned `True` and skipped upscaling, even though upscaled files were missing from Google Drive.

---

## Approach
1. **Absolute Path Resolution in `google_drive.py`**:
   - In `GoogleDriveService._get_credentials()`, resolve `client_secrets_path` and `token_path` against `_PROJECT_ROOT` if relative.
2. **Google Drive Primary Completion Check**:
   - For `stage_name == "upscaling"`, query Google Drive folder `Clipart/main_data/<date_folder>/<theme_slug>/`.
   - Only return `True` (skip) if Google Drive actually contains all upscaled PNGs.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/services/google_drive.py` — Resolve credential file paths against `_PROJECT_ROOT`.
- `craftdesk_api/services/pipeline_runner.py` — Update Stage 3 completion check to require Google Drive PNG confirmation.

---

## Steps
1. Update `_get_credentials()` in `etsy_pipeline/services/google_drive.py` to resolve paths relative to `_PROJECT_ROOT`.
2. Update `_is_stage_100pct_complete()` in `craftdesk_api/services/pipeline_runner.py` for `upscaling`.
3. Update `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`.
4. Format code, test, and rebuild graph (`python scripts/build_graph.py`).
