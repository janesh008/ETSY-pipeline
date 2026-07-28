# Plan: 6-Stage Pipeline Execution & GCS Prompt Injection

**Date:** 2026-07-28  
**Status:** approved  
**Related:** [`etsy_pipeline/pipeline/CONTEXT.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/pipeline/CONTEXT.md)

---

## Problem
Currently `craftdesk_api` (`PipelineRunnerService`) uses dummy `asyncio.sleep` simulations to fake pipeline progress for 6 mock stages. It is disconnected from the real Python pipeline workers in `etsy_pipeline/workers/`. In addition, prompt generation is handled beforehand in Prompt Studio and stored to GCS as `.txt` files (`Clipart/<date>/<theme_slug>/<theme_slug>.txt`). The user needs to pick any prompt file from GCS/local storage in the UI, and run the real 6-stage execution pipeline (Image Gen → BG Removal → AI Upscale → Mockup → Clickable PDF → Metadata) with real-time UI progress bars, ETA, image counts, and logs, without modifying core worker business logic or storage routines.

---

## Clarifying questions & answers
- Q: Should prompt generation be included in the pipeline execution stages?  
  A: No, prompt generation is already complete in Prompt Studio and saved to GCS. The 6 pipeline execution stages are Image Gen, BG Removal, Upscale, Mockups, Clickable PDF, and Metadata Generation.
- Q: Should we modify core worker logic or storage routines in `etsy_pipeline`?  
  A: No, keep all worker business logic, GCS uploads, Drive delivery, and local file structures unchanged.
- Q: Should estimated cost be shown in the UI?  
  A: No, exclude cost display. Show progress %, image counters, elapsed time, and ETA.

---

## Approach
1. **Model & Schema Support**:
   - `etsy_pipeline/models/job.py`: Add prompt file injection helper to `Job` so it parses injected GCS/local prompt `.txt` files directly into `job.prompts`. Ensure `StageResult` tracks `images_done`, `images_total`, `elapsed_seconds`, and estimated time remaining (ETA).
   - `craftdesk_api/schemas/pipeline.py`: Update `StageStatus` and `PipelineStartRequest` to include 6 canonical stage names, progress %, ETA, elapsed time, image counters, and stderr logs.

2. **Backend Execution Service (`craftdesk_api/services/pipeline_runner.py`)**:
   - Define the 6 canonical execution stages: `image_gen`, `bg_removal`, `upscaling`, `mockup_creation`, `pdf_generation`, `metadata_generation`.
   - In `create_job()`, load and parse the selected GCS or local prompt file using `PromptWorker._parse_response` to populate `job.prompts`.
   - In `run_full_pipeline_async()`, execute `etsy_pipeline` worker instances sequentially in background threads (`asyncio.to_thread`):
     - Stage 1: `ImageWorker.run(job)`
     - Stage 2: `BackgroundRemovalWorker.run(job)`
     - Stage 3: `UpscaleWorker.run(job)`
     - Stage 4 & 5: `MockupWorker.run(job)` (generates mockups and clickable PDF)
     - Stage 6: `MetadataWorker.run(job)`
   - Dynamically update real-time progress, image counts, ETA, and stderr logs in `_PIPELINE_JOBS_STORE`.

3. **Frontend UI Integration (`craftdesk_web/src/app/pipeline/page.tsx`)**:
   - Fetch GCS prompt files from `/api/v1/prompts/files`.
   - Connect UI to `POST /api/v1/pipeline/jobs` and WebSocket stream `/api/v1/pipeline/jobs/{job_id}/stream`.
   - Display live progress bars, image counters (`12/24 images`), elapsed time, and ETA for each stage.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/models/job.py` — Add prompt file parsing/injection support and ETA/progress fields to `StageResult`.
- `craftdesk_api/schemas/pipeline.py` — Update schemas for 6 pipeline stages, ETA, elapsed seconds, and image progress metrics.
- `craftdesk_api/services/pipeline_runner.py` — Replace mock dummy sleep with real worker execution, ETA calculation, and stage progress updates.
- `craftdesk_api/routers/pipeline.py` — Update router endpoints to handle GCS prompt file injection and stream real worker progress.
- `craftdesk_web/src/app/pipeline/page.tsx` — Update frontend UI to trigger real pipeline execution and display live stage progress bars & ETA.

**Out of scope:**
- Modifying worker internal logic or GCS/Drive delivery mechanisms inside `etsy_pipeline/workers/`.
- Modifying ComfyUI workflows or rembg/Real-ESRGAN model architectures.

---

## Risks & edge cases
- **GCS Download Availability**: If running locally without GCS credentials, fallback to local `output/Clipart/<date>/<theme_slug>/<theme_slug>.txt`.
- **Long-Running Thread Execution**: Worker stages execute heavy CUDA/subprocess tasks. Running them with `asyncio.to_thread` ensures the FastAPI uvicorn event loop remains responsive for status queries and WebSocket streaming.

---

## Steps
1. Update `Job` and `StageResult` in `etsy_pipeline/models/job.py`.
2. Update schemas in `craftdesk_api/schemas/pipeline.py`.
3. Update `PipelineRunnerService` in `craftdesk_api/services/pipeline_runner.py` to run real `etsy_pipeline` worker instances and update progress metrics.
4. Update `craftdesk_api/routers/pipeline.py` to support `prompt_file_path` injection and live streaming.
5. Update `craftdesk_web/src/app/pipeline/page.tsx` for real stage progress bars, ETA, and GCS file selection.
6. Verify implementation via linting, type checks, and API execution test.

---

## Rollback
Git revert changes to `craftdesk_api/services/pipeline_runner.py`, `craftdesk_api/routers/pipeline.py`, `etsy_pipeline/models/job.py`, and `craftdesk_web/src/app/pipeline/page.tsx`.
