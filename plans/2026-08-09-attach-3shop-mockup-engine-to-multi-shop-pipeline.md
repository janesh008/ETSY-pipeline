# Plan: Attach 3-Shop Mockup Engine to Multi-Shop Pipeline

**Date:** 2026-08-09  
**Status:** Approved & In Progress  

---

## Problem Statement

The newly built multi-shop rendering engine (`RenderingOrchestrator`) supports 3 shops (`pixelbarstudio`, `luna_cliparts`, `crisp_png_co`) and Photorealistic Lifestyle product mockups. However, `MockupWorker` in `etsy_pipeline/workers/mockup_worker.py` was calling the legacy single-shop `src.main` script. We need to wire `RenderingOrchestrator` into the `multi_shop` pipeline stage (`multi_shop_mockups`) while keeping the existing `single_shop` pipeline stage (`mockups`) 100% separate and unchanged.

---

## Proposed Approach

1. **Keep Single-Shop and Multi-Shop Pipelines 100% Separate**:
   - `single_shop` pipeline stage (`mockups`): Renders `pixelbarstudio` only directly into `output/<date>/<theme>/mockups/`.
   - `multi_shop` pipeline stage (`multi_shop_mockups`): Renders all selected shops (`pixelbarstudio`, `luna_cliparts`, `crisp_png_co`) into `output/<date>/<theme>/mockups/<shop_id>/`.

2. **Integrate `RenderingOrchestrator` into `MockupWorker`**:
   - In `MockupWorker.run(job)`:
     - Check stage context (`mockups` vs `multi_shop_mockups`).
     - Determine target shops: `["pixelbarstudio"]` for single-shop; `job.selected_shops` or `["pixelbarstudio", "luna_cliparts", "crisp_png_co"]` for multi-shop.
     - Instantiate `RenderingOrchestrator(rendering_root)`.
     - Execute per-shop rendering loop with `try...except` error isolation so a failure in one shop doesn't crash the pipeline for other shops.

3. **Wire Stage Name to Pipeline & API Runners**:
   - Update `PipelineOrchestrator` (`etsy_pipeline/pipeline/orchestrator.py`) to map `"multi_shop_mockups": self._mockup_worker`.
   - Update `craftdesk_api` (`craftdesk_api/services/pipeline_runner.py`) to handle `"multi_shop_mockups"` in `_execute_stage_worker_sync()`.

---

## Affected Files

- `etsy_pipeline/workers/mockup_worker.py` — Update `_run_mockup_creator()` to use `RenderingOrchestrator` with per-shop error handling.
- `etsy_pipeline/pipeline/orchestrator.py` — Register `"multi_shop_mockups"` in `worker_map`.
- `craftdesk_api/services/pipeline_runner.py` — Register `"multi_shop_mockups"` in stage execution mapping.
- `tests/test_mockup_worker_integration.py` — [NEW] Unit tests for single-shop and multi-shop mockup worker execution.

---

## Implementation Steps

1. Update `etsy_pipeline/workers/mockup_worker.py`.
2. Update `etsy_pipeline/pipeline/orchestrator.py`.
3. Update `craftdesk_api/services/pipeline_runner.py`.
4. Create unit test `tests/test_mockup_worker_integration.py` and run `pytest`.
