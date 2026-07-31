# Plan: Dual Local & VM Resilience for GCS & Google Drive Services

**Date:** 2026-07-31
**Status:** done
**Related:** [etsy_pipeline/services/doc/HIGH_LEVEL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/doc/HIGH_LEVEL.md)

---

## Problem
In local development, calling API endpoints like `/api/v1/prompts/files` triggers `ECONNRESET` / `socket hang up` Next.js proxy errors. This happens because GCS and Google Drive client initializations attempt to contact the GCP metadata server (`169.254.169.254`), which hangs for 20-30 seconds on non-GCP local Windows machines before timing out, exceeding Next.js proxy limits.

---

## Approach
1. Add a fast, non-blocking check (`is_available()`) to `GCSStore` and `GoogleDriveService` that verifies if GCP credentials or GCP environment exist before attempting network operations.
2. Set strict short network timeouts (2s) on GCS/Drive network client instantiations so that if credentials or network are unreachable on local machines, execution fails fast and immediately falls back to local disk storage (`output/Clipart/`, `output/pdf/`, etc.).
3. Update `craftdesk_api/routers/prompts.py` (`list_prompt_files`) to scan local disk storage immediately when GCS is unavailable or fails, ensuring responses return in `< 50ms`.

**Alternatives considered:**
- Hardcoding local mode via an environment variable — rejected because we want zero manual environment configuration changes when running locally vs deploying on GCP VM.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/services/gcs_store.py` — Add `is_available()` check and non-blocking initialization safeguard.
- `craftdesk_api/routers/prompts.py` — Fast local disk fallback for `list_prompt_files` without waiting for GCP metadata timeout.
- `etsy_pipeline/services/google_drive.py` — Ensure Drive authentication failure falls back cleanly to local path handling.

**Out of scope:**
- Modifying Next.js UI component rendering logic.

---

## Risks & edge cases
- *Risk*: Local environment without GCP credentials cannot read files existing solely in GCS bucket.
- *Mitigation*: Local files in `output/Clipart/` are read instantly. When deployed on GCP VM, both GCS and local files are scanned seamlessly.

---

## Steps
1. Add `is_gcp_available()` helper and fast timeout in `etsy_pipeline/services/gcs_store.py`.
2. Update `craftdesk_api/routers/prompts.py` to use non-blocking GCS check before scanning GCS blobs in `list_prompt_files`.
3. Update `etsy_pipeline/services/google_drive.py` to catch GCP credential/network errors gracefully.
4. Verify `/api/v1/prompts/files` response speed locally using `python -c` script.
5. Update `etsy_pipeline/services/doc/HIGH_LEVEL.md` and `DETAILED.md` to document the dual Local & VM fallback behavior.

---

## Rollback
Revert changes to `etsy_pipeline/services/gcs_store.py`, `craftdesk_api/routers/prompts.py`, and `etsy_pipeline/services/google_drive.py` via git.
