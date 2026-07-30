# Plan: Fix Pipeline Execution current_stage State Discrepancy

**Date:** 2026-07-30
**Status:** approved
**Related:** [craftdesk_api/doc/PIPELINE_ARCHITECTURE.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)

---

## Problem
When Stages 1–3 (`image_gen`, `bg_removal`, `upscaling`) are skipped or completed, `current_stage` in `GET /api/v1/pipeline/jobs/{job_id}` responses remained stuck as `"image_gen"` instead of reflecting the actual pending/running stage (`"mockup_creation"`).

---

## Approach
1. In `craftdesk_api/services/pipeline_runner.py`, update `job_data["current_stage"] = s_name` at the start of evaluating each stage in `run_full_pipeline_async()`.
2. In `craftdesk_api/routers/pipeline.py`, update `_build_job_response()` to dynamically set `current_stage` to the first non-completed stage (`running` or `pending`) whenever `status == "running"`.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/pipeline_runner.py` — Update `current_stage` assignment in `run_full_pipeline_async()`.
- `craftdesk_api/routers/pipeline.py` — Add dynamic `current_stage` synchronization in `_build_job_response()`.

**Out of scope:**
- Modifying frontend status badge rendering.

---

## Risks & edge cases
- *Edge case:* Job fails on stage 4 (`mockup_creation`).
  *Mitigation:* Keep `current_stage` set to the failing stage when `status == "failed"`.

---

## Steps
1. Modify `craftdesk_api/services/pipeline_runner.py` to update `current_stage` during stage loop evaluation.
2. Modify `craftdesk_api/routers/pipeline.py` to dynamically sync `current_stage` in `_build_job_response()`.
3. Run linting (`python -m ruff check . --fix`), type checking (`python -m mypy etsy_pipeline`), and tests (`pytest`).
4. Update documentation in `craftdesk_api/doc/DETAILED.md`.
