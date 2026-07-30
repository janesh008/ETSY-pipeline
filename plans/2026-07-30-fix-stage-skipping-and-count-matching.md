# Plan: Exact Image Count Stage Skipping & Downstream Asset Completion

**Date:** 2026-07-30
**Status:** approved
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)

---

## Problem
When starting or re-running a pipeline execution, Stage 1 (`image_gen`) re-runs from scratch even if previously completed. This happens because Stage 2 (`bg_removal`) intentionally purges `raw_images/` post-stage cleanup to save disk space. When `_is_stage_100pct_complete(job, "image_gen")` checks `raw_images/`, it finds 0 files and returns `False`, failing to check if downstream stage assets (`no_bg/` or upscaled Drive images) already match `job.total_prompt_count`. Additionally, `run_full_pipeline_async()` did not check `stage.get("status") == "completed"`.

---

## Approach
1. In `PipelineRunnerService._is_stage_100pct_complete(job, stage_name)`:
   - For `image_gen`: Check `raw_images/` count $\ge$ `job.total_prompt_count` (local/GCS). If not found, check downstream `no_bg/` count (local/GCS/Drive) $\ge$ `job.total_prompt_count` or upscaled count on Drive $\ge$ `job.total_prompt_count`.
   - For `bg_removal`: Check `no_bg/` count $\ge$ `job.total_prompt_count` (local/GCS/Drive). If not found, check downstream upscaled count on Drive $\ge$ `job.total_prompt_count`.
   - For `upscaling`: Check Google Drive upscaled folder count $\ge$ `job.total_prompt_count`.
   - For `mockup_creation` / `pdf_generation`: Check mockup count $\ge 4$ and valid PDF file existence.
   - For `metadata_generation`: Check `job.metadata` title and tags count $\ge 5$.

2. In `PipelineRunnerService.run_full_pipeline_async()`:
   - Update stage skip check to:
     ```python
     if stage.get("status") == "completed" or cls._is_stage_100pct_complete(job, s_name):
     ```

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/pipeline_runner.py` — Update `_is_stage_100pct_complete` and `run_full_pipeline_async`.
- `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md` & `craftdesk_api/doc/DETAILED.md` — Update architecture docs.

**Out of scope:**
- Modifying worker execution logic for ComfyUI, rembg, or Real-ESRGAN.

---

## Steps
1. Update `_is_stage_100pct_complete` and `run_full_pipeline_async` in `craftdesk_api/services/pipeline_runner.py`.
2. Run unit tests `pytest craftdesk_api/tests/test_pipeline.py`.
3. Update architecture docs.
4. Run `ruff check`.
5. Rebuild repo graph (`python scripts/build_graph.py`).
