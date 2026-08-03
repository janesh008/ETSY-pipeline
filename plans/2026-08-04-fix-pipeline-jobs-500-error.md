# Plan: Fix HTTP 500 Internal Server Error on /api/v1/pipeline/jobs

**Date:** 2026-08-04
**Status:** approved
**Related:** [craftdesk_api/doc/DETAILED.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/DETAILED.md)

---

## Problem
Calling `POST /api/v1/pipeline/jobs` or `GET /api/v1/pipeline/jobs` in production returns an unhandled HTTP 500 Internal Server Error when GCP credentials are missing, GCS prompt files cannot be located, or when querying job lists.

---

## Approach
1. Handle GCS download and prompt file loading errors gracefully in `PipelineRunnerService.create_job`:
   - Catch `google.auth.exceptions.DefaultCredentialsError` and GCS exceptions when initializing `storage.Client()`.
   - Raise `ValueError` with clear messages for missing prompts or prompt files.
2. In `craftdesk_api/routers/pipeline.py`:
   - Catch `ValueError` and `FileNotFoundError` in `start_pipeline_job` and raise `HTTPException(status_code=400 or 404)` with informative details instead of crashing with HTTP 500.
   - Remove unused database dependency `db: AsyncSession = Depends(get_db)`.
   - Add `GET /api/v1/pipeline/jobs` endpoint that lists pipeline jobs for the authenticated user.
3. In `craftdesk_api/services/pipeline_runner.py`:
   - Add `list_jobs(user_id: str)` method to return all cached jobs belonging to `user_id`.
4. Add comprehensive unit tests in `craftdesk_api/tests/test_pipeline.py`.

**Alternatives considered:**
- Returning empty dummy job objects on error — rejected per Karpathy guidelines (no swallowing errors or returning dummy data; propagate clear HTTP 400/404 exception details).

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/pipeline_runner.py` — Add `list_jobs()`, handle GCS auth errors in `create_job()`.
- `craftdesk_api/routers/pipeline.py` — Catch `ValueError` in `start_pipeline_job`, remove unused `db` dependency, add `GET /api/v1/pipeline/jobs`.
- `craftdesk_api/tests/test_pipeline.py` — Unit tests for error handling and job listing.

**Out of scope:**
- Modifying ComfyUI execution logic or model rendering pipelines.

---

## Risks & edge cases
- GCS authentication missing in production — mitigated by logging warning and checking local disk fallback cleanly, then returning HTTP 400/404 if prompt file is unavailable.

---

## Steps
1. Update `craftdesk_api/services/pipeline_runner.py` to add `list_jobs(user_id: str)` and protect GCS storage client initialization against `DefaultCredentialsError`.
2. Update `craftdesk_api/routers/pipeline.py` to wrap `create_job` in try/except returning HTTP 400/404, remove unused `db` dependency, and add `GET /jobs` route.
3. Add unit tests in `craftdesk_api/tests/test_pipeline.py`.
4. Run `ruff` and `pytest` to verify changes.
5. Update `craftdesk_api/doc/DETAILED.md` and `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`.
6. Regenerate `.repo-graph/graph.json` via `python scripts/build_graph.py`.

---

## Rollback
Git revert changes to `craftdesk_api/services/pipeline_runner.py`, `craftdesk_api/routers/pipeline.py`, and `craftdesk_api/tests/test_pipeline.py`.
