# Plan: Fix Mockup Count and Widget UX

**Date:** 2026-08-04
**Status:** approved
**Related:** [etsy mockup creator/src/renderer.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/src/renderer.py), [craftdesk_api/services/pipeline_runner.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/pipeline_runner.py), [craftdesk_web/src/context/PipelineContext.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/context/PipelineContext.tsx)

---

## Problem
1. The text overlay on generated hero mockups displays a count higher than the actual number of transparent images (e.g. 230 instead of 130). This is due to file path duplication (files residing in both the parent directory and subfolders) when absolute paths are indexed.
2. The "BATCH FINISHED" floating widget persistently reappears after the user dismisses it because the background status polling repopulates the batch queue with jobs from the database cache.
3. Idle background polling makes redundant API calls every 4 seconds when the pipeline is inactive.
4. Stage totals for PDF wrap generation and Metadata generation are set to the raw image count (e.g. 138 / 138), which is incorrect since they only build a single file/record.

---

## Approach
1. Deduplicate files in `etsy mockup creator/src/renderer.py` by filename (basename) rather than absolute path strings before computing the bundle count overlay.
2. Update backend `PipelineRunnerService.create_job` to set proper total counts for mockup creation, PDF generation, and metadata generation stages.
3. Split PDF generation progress checks from mockup checks in `PipelineRunnerService.run_stage_execution`.
4. Add `showFloatingWidget` state (defaulting to `false`) to `PipelineContext.tsx`. Set it to `true` when a batch starts or is sync-detected, and set to `false` when dismissed.
5. Control polling in `PipelineContext.tsx`: poll frequently only when a job is active/running, otherwise stop polling or sync at a low frequency.
6. Hide the floating widget in `FloatingPipelineWidget.tsx` if `showFloatingWidget` is false, and update the close button to trigger dismissal.

---

## Scope

**Files/modules touched:**
- `etsy mockup creator/src/renderer.py`
- `craftdesk_api/services/pipeline_runner.py`
- `craftdesk_web/src/context/PipelineContext.tsx`
- `craftdesk_web/src/components/pipeline/FloatingPipelineWidget.tsx`

**Out of scope:**
- Modifying `rembg` background removal models or upscaler networks.

---

## Steps
1. Modify `etsy mockup creator/src/renderer.py` (already completed in active memory/edit).
2. Modify `craftdesk_api/services/pipeline_runner.py` to fix stage totals and progress checks.
3. Modify `craftdesk_web/src/context/PipelineContext.tsx` to handle `showFloatingWidget` state and conditional polling.
4. Modify `craftdesk_web/src/components/pipeline/FloatingPipelineWidget.tsx` to respect `showFloatingWidget` and trigger dismissal.
5. Run automated tests and verify tsc/lint rules.
6. Update walkthrough.md.

---

## Rollback
Git checkout modified files.
