# Plan: Google Drive Service Account Key Authentication & Headless Protection

**Date:** 2026-07-29  
**Status:** approved  
**Related:** [`etsy_pipeline/services/google_drive.py`](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/google_drive.py), [`.env`](file:///d:/Janesh/ETSY/ETSY-pipeline/.env)

---

## Problem
`GoogleDriveService._get_credentials()` threw `InstalledAppFlow: could not locate runnable browser. Make sure you run this script in an environment where a web browser can open.` because OAuth token refresh failed and `run_local_server()` tried to launch a desktop browser on a headless VM/server.

---

## Approach
1. **Service Account Support in `GoogleDriveService._get_credentials()`**:
   - Inspect client secret JSON file.
   - If `"type": "service_account"` (e.g. `cred/gen-lang-client-0665218091-2ad1abf3315e.json`), authenticate using `service_account.Credentials.from_service_account_file()`. Service Accounts require no browser login and never expire.
2. **Headless Browser Protection**:
   - Wrap `InstalledAppFlow.run_local_server()` in a try/except. If browser launch fails, catch `Exception` and raise a clear `ConfigurationError`.
3. **Update `.env`**:
   - Set `GOOGLE_DRIVE_CLIENT_SEC_JSON=cred/gen-lang-client-0665218091-2ad1abf3315e.json`.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/services/google_drive.py` — Support Service Account JSON keys and headless browser exception handling.
- `.env` — Set `GOOGLE_DRIVE_CLIENT_SEC_JSON=cred/gen-lang-client-0665218091-2ad1abf3315e.json`.

---

## Steps
1. Update `_get_credentials()` in `etsy_pipeline/services/google_drive.py`.
2. Update `.env`.
3. Update documentation in `etsy_pipeline/workers/doc/DETAILED.md` and `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`.
4. Format code, test, and rebuild graph (`python scripts/build_graph.py`).
