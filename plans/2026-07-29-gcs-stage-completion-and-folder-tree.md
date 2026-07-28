# Plan: GCS Stage Completion Path Fix & Date-Wise Collapsible Folder Tree UI

**Date:** 2026-07-29  
**Status:** approved  
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)

---

## Problem
1. When re-running a pipeline job, Stage 1 (`image_gen`) restarted from scratch instead of being marked completed because `_is_stage_100pct_complete` did not query the GCS bucket prefix (`Clipart/<date>/<theme>/raw_images/`) or local `output/Clipart/...` directory correctly.
2. The left panel in the Pipeline Runner page displayed prompt files as a flat list, making it difficult to navigate date-wise folders and themes.

---

## Approach
1. **GCS & Local Path Resolution Fix**:
   - In `PipelineRunnerService._is_stage_100pct_complete()`:
     - Query GCS objects with prefix `Clipart/<date_folder>/<theme_slug>/<stage_name>/`.
     - Check local disk paths `output/Clipart/<date_folder>/<theme_slug>/<stage_name>/` and `output/<date_folder>/<theme_slug>/<stage_name>/`.
     - If file count $\ge$ `job.total_prompt_count`, mark stage as `Completed ✅` and skip worker.
2. **Date-Wise Collapsible Folder Tree UI**:
   - In `craftdesk_web/src/app/pipeline/page.tsx`:
     - Group `promptFiles` by `file.date` into `Record<string, PromptFile[]>`.
     - Render collapsible date folder accordions with expand/collapse arrows (`ChevronDown`/`ChevronRight`) and theme item counts.
     - Allow sellers to expand/collapse date groups and select themes.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/pipeline_runner.py` — Update `_is_stage_100pct_complete` to check GCS prefix `Clipart/<date>/<theme>/<stage>/` and local `output/Clipart/...`.
- `craftdesk_web/src/app/pipeline/page.tsx` — Add `openDates` state and render date-grouped collapsible folder tree in left panel.

---

## Steps
1. Update `_is_stage_100pct_complete()` in `craftdesk_api/services/pipeline_runner.py`.
2. Add date grouping and collapsible folder tree rendering in `craftdesk_web/src/app/pipeline/page.tsx`.
3. Update `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`.
4. Run formatting, type checks, and rebuild repo graph (`python scripts/build_graph.py`).
