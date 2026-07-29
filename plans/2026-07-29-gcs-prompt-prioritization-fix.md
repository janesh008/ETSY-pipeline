# Plan: Prioritize GCS Bucket Prompts & Fix UI Tag and Resolution

**Date:** 2026-07-29  
**Status:** approved  
**Related:** [`craftdesk_api/routers/prompts.py`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/prompts.py), [`craftdesk_api/services/pipeline_runner.py`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/pipeline_runner.py), [`craftdesk_web/src/app/pipeline/page.tsx`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/pipeline/page.tsx)

---

## Problem
1. `list_prompt_files()` in `prompts.py` scanned local disk `output/Clipart/` first. For any file found locally, it attached `local_path`, causing the left panel UI to display `💾 Local` tag for every prompt, even when hosted on GCS.
2. When launching a job for a prompt with `local_path`, `create_job()` attempted to read the file locally on the VM. If the file was missing on local disk, `Path.exists()` returned `False`, causing job initialization to fail with "file does not exist".

---

## Approach
1. **Prioritize GCS Discovery in `list_prompt_files()`**:
   - Scan GCS bucket `gs://<bucket>/Clipart/` **FIRST**.
   - Attach `gcs_path` as primary prompt identifier and set `is_gcs = True`.
   - Scan local disk `output/Clipart/` second to append any non-GCS prompt files.
2. **GCS-First Prompt Loading in `create_job()`**:
   - Always attempt to fetch prompt text from **GCS (`gs://...`) FIRST**.
   - If a relative or local path is passed (e.g. `output/Clipart/<date>/<theme>/<file>.txt`), resolve corresponding GCS URI (`gs://<bucket>/Clipart/<date>/<theme>/<file>.txt`) and download from GCS.
3. **Update UI Tag**:
   - Display `☁️ GCS` badge for all GCS-backed prompt files.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/routers/prompts.py` — Scan GCS first in `list_prompt_files()`.
- `craftdesk_api/services/pipeline_runner.py` — Prioritize GCS downloading in `create_job()`.
- `craftdesk_web/src/app/pipeline/page.tsx` — Display `☁️ GCS` badge for GCS prompts.

---

## Steps
1. Re-order `list_prompt_files()` in `craftdesk_api/routers/prompts.py` to scan GCS first.
2. Update `create_job()` in `craftdesk_api/services/pipeline_runner.py` to try GCS first.
3. Update prompt tag rendering in `craftdesk_web/src/app/pipeline/page.tsx`.
4. Update `craftdesk_api/doc/DETAILED.md`.
5. Format code, test, and rebuild graph (`python scripts/build_graph.py`).
