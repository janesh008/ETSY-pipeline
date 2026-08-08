# Plan: Fix Mockup Stage Execution & JPEG Detection

**Date:** 2026-08-09  
**Status:** Approved & In Progress  

---

## Problem Statement

When themes have `no_bg` and `upscaled` images, Stage 4/5 was previously skipping execution or failing to upload JPEG mockups (`.jpg` / `.jpeg`) to GCS. As a result, `job.mockups` remained empty and GCS Theme Selector showed `[ No Mockups ]`.

---

## Root Causes Identified

1. **JPEG Exclusion in `MockupWorker`**: `MockupWorker.run()` searched exclusively for `*.png`. Since Hero and Lifestyle mockups are saved as optimized `.jpg` files, 0 files were uploaded to GCS under `Clipart/<date>/<theme>/mockups/`.
2. **Stage Name & Extension Mismatch in `_is_stage_100pct_complete`**: `PipelineRunnerService` stage completion check didn't handle `"mockups"` / `"multi_shop_mockups"` stage names or `.jpg` extensions.

---

## Proposed Fixes

1. Update `MockupWorker.run()` to collect and upload all supported image extensions (`.png`, `.jpg`, `.jpeg`, `.webp`).
2. Update `_is_stage_100pct_complete()` in `craftdesk_api/services/pipeline_runner.py` to match `"mockups"` and `"multi_shop_mockups"` stage names and inspect `.jpg` / `.jpeg` files on local VM disk and GCS bucket.

---

## Files to Modify

- `etsy_pipeline/workers/mockup_worker.py`
- `craftdesk_api/services/pipeline_runner.py`
- `tests/test_jpeg_mockup_detection.py` [NEW]
