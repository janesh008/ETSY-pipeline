# Plan: Module-Level Resiliency & Date Folder Preservation

**Date:** 2026-07-29  
**Status:** approved  
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)

---

## Problem
1. When selecting a prompt file from a past date (e.g. `2026-07-22`), starting pipeline execution creates a new directory with today's date (`2026-07-29`), causing file location inconsistencies across stages.
2. If a pipeline job crashes or browser refreshes, re-running the job restarts all stages from 0%, even if previous stages (e.g. Image Gen) were 100% completed.
3. In progress tracking, stages like `bg_removal` were freezing at 90% with 0 items processed because `stage.images_total` and `stage.images_done` were not properly populated or reset before starting worker loops.

---

## Clarifying questions & answers
- Q: Should incomplete stages perform item-level skipping?  
  A: No, skip item-level partial resumption. If a stage was interrupted midway, restart that stage cleanly from the beginning (0% → 100%). Skip only 100% finished stages.
- Q: How to handle past date folders?  
  A: Extract `date_folder` directly from `prompt_file_path` (e.g. `Clipart/2026-07-22/...`). All raw images, `no_bg/`, `upscaled/`, `mockups/`, `pdf/`, and metadata must stay inside `2026-07-22`.

---

## Approach
1. **Date Folder Extraction**:
   - In `PipelineRunnerService.create_job()`, parse `date_folder` from `prompt_file_path` regex `Clipart/(\d{4}-\d{2}-\d{2})/`.
   - Pass `date_folder` to `Job(date_folder=extracted_date)`.
2. **Module-Level Checkpoint Verification**:
   - In `PipelineRunnerService.run_full_pipeline_async()`:
     - Check if 100% of stage output files exist in local disk or GCS/Drive.
     - If 100% finished: set stage status to `completed`, `progress_percent = 100`, `images_done = total`, and advance immediately to the next stage.
     - If incomplete: reset stage to `pending` with `progress_percent = 0` and run worker from start.
3. **Worker Progress Bar & Item Counter Fixes**:
   - Explicitly set `stage.images_total = total` and `stage.images_done = 0` at worker entry.
   - Update `stage.images_done = idx` on every item in `image_worker.py`, `bg_removal_worker.py`, `upscale_worker.py`, and `mockup_worker.py`.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/models/job.py` — Support passing custom `date_folder` on initialization.
- `craftdesk_api/services/pipeline_runner.py` — Add date folder extraction and module-level 100% completion verification checks.
- `etsy_pipeline/workers/image_worker.py` — Ensure `images_done` and `images_total` are tracked continuously.
- `etsy_pipeline/workers/bg_removal_worker.py` — Initialize `images_total` and update `images_done` on every item.
- `etsy_pipeline/workers/upscale_worker.py` — Initialize `images_total` and update `images_done` on every item.
- `etsy_pipeline/workers/mockup_worker.py` — Set `images_total` and update `images_done`.
- `craftdesk_web/src/app/pipeline/page.tsx` — Render skipped/recovered stage badges smoothly.

**Out of scope:**
- Item-level partial recovery inside worker loops.
- Altering core worker image generation, rembg, or Real-ESRGAN algorithms.

---

## Steps
1. Update `Job` model in `etsy_pipeline/models/job.py` to preserve custom `date_folder`.
2. Add date extraction and `_is_stage_100pct_complete` in `craftdesk_api/services/pipeline_runner.py`.
3. Update `images_total` and `images_done` tracking in `bg_removal_worker.py`, `image_worker.py`, `upscale_worker.py`, and `mockup_worker.py`.
4. Update `craftdesk_api/doc/PIPELINE_ARCHITECTURE.md` to document date retention and module-level stage skipping.
5. Format, test, and regenerate graph (`python scripts/build_graph.py`).

---

## Rollback
Git revert changes to `craftdesk_api/services/pipeline_runner.py`, `etsy_pipeline/models/job.py`, and `etsy_pipeline/workers/`.
