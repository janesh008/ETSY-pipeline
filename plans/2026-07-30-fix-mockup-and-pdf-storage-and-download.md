# Plan: Fix Mockup & PDF Storage Verification, Output Population, and PDF Download

**Date:** 2026-07-30  
**Status:** approved  
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)

---

## Problem
1. `MockupWorker` generated mockups locally, but never populated `job.mockups = [...]`. As a result, `job_data["mockups"]` remained empty `[]`, displaying placeholder text instead of thumbnail previews.
2. `_is_stage_100pct_complete` returned `True` for Stage 4/5 based on GCS keys even when local VM disk files were missing, skipping `MockupWorker` in 0s without populating `job.pdf_path` or `job.mockups`.
3. `GET /api/v1/pipeline/jobs/{job_id}/pdf` returned a `404 Not Found` JSON error response when local `pdf_path` was missing, causing browsers to download `pdf.json` instead of a `.pdf` file.

---

## Approach
1. **`etsy_pipeline/workers/mockup_worker.py`**:
   - In `MockupWorker.run()`: Set `job.mockups = sorted([str(f) for f in mockups_local_dir.glob("*.png")])` and `job.hero_image_url = job.mockups[0]` if non-empty.

2. **`craftdesk_api/services/pipeline_runner.py`**:
   - In `_is_stage_100pct_complete()`: Require local VM disk files (`pdf_file.exists()` and `len(mockup_dir.glob("*.png")) >= 4`).
   - When complete, populate `job.pdf_path`, `job.pdf_drive_link`, `job.mockups`, `job.hero_image_url`, and `job_data[...]`.

3. **`craftdesk_api/routers/pipeline.py`**:
   - In `download_pipeline_job_pdf()`: If `pdf_local_path` is missing from disk, check output root or GCS to restore the `.pdf` file before returning `FileResponse(path, media_type="application/pdf")`.

4. **Automated Tests**:
   - Add explicit assertions verifying VM disk files exist (`Path(job.pdf_path).exists()`, `Path(m).exists()`) and that `download_pipeline_job_pdf` returns `application/pdf`.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/workers/mockup_worker.py` — Populate `job.mockups` and `job.hero_image_url`.
- `craftdesk_api/services/pipeline_runner.py` — Require local VM files in `_is_stage_100pct_complete` for Stage 4/5.
- `craftdesk_api/routers/pipeline.py` — Restore PDF file on demand in `download_pipeline_job_pdf`.
- `tests/test_mockup_worker.py` & `craftdesk_api/tests/test_pipeline.py` — Add VM disk and PDF response test assertions.

---

## Steps
1. Update `mockup_worker.py`, `pipeline_runner.py`, and `routers/pipeline.py`.
2. Update unit tests.
3. Run `pytest tests/test_mockup_worker.py craftdesk_api/tests/test_pipeline.py -v`.
4. Run `ruff check`.
5. Rebuild graph (`python scripts/build_graph.py`).
