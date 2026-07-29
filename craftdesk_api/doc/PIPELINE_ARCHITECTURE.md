# CraftDesk API — 6-Stage Pipeline Execution & Architecture Guide

This document explains the technical architecture, data flow, GCS prompt injection, worker stage execution, ETA calculation, and stage retry mechanisms for the CraftDesk Asset Generation Pipeline.

---

## 💡 Executive Summary

`craftdesk_api` bridges the web frontend (`craftdesk_web`) to the core Python pipeline package (`etsy_pipeline`). It orchestrates 6 asset generation stages using prompt files generated beforehand in Prompt Studio and saved to Google Cloud Storage (GCS).

```
                  ┌──────────────────────────────────────────────┐
                  │ 1. PROMPT STUDIO (Prompt Generation Phase)   │
                  │    - Generates or receives prompt text      │
                  │    - Saves to GCS & local disk               │
                  │    - Path: Clipart/<date>/<slug>/<slug>.txt  │
                  └──────────────────────┬───────────────────────┘
                                         │ Selected Prompt File
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        2. CRAFTDESK 6-STAGE EXECUTION PIPELINE                         │
│                                                                                        │
│  Stage 1: 🎨 Image Generation (ComfyUI HTTP API :8188)                                │
│  Stage 2: ✂️ Background Removal (rembg isnet-general-use)                              │
│  Stage 3: 🔍 AI Upscaling (Real-ESRGAN 4x-UltraSharp & Google Drive upload)            │
│  Stage 4: 🖼️ Mockup Creation (etsy mockup creator subprocess)                           │
│  Stage 5: 📄 Clickable PDF Wrap Generation (ReportLab A4 catalog wrapper)              │
│  Stage 6: 📝 Etsy Metadata Generation (300 DPI SEO description & 13 tags)              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Key File Locations & Responsibilities

| File Path | Component | Responsibility |
|---|---|---|
| `craftdesk_api/routers/pipeline.py` | FastAPI Router | Exposes REST endpoints (`POST /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/stages/{stage}/retry`) and WebSocket (`/jobs/{id}/stream`). |
| `craftdesk_api/schemas/pipeline.py` | Pydantic Schemas | Defines API contracts for `PipelineStartRequest`, `StageStatus` (with ETA, elapsed time, item progress counters), and `PipelineJobResponse`. |
| `craftdesk_api/services/pipeline_runner.py` | Orchestration Service | Loads GCS prompt files into `Job`, manages background thread execution (`asyncio.to_thread`) of `etsy_pipeline` workers, tracks stage progress, and computes ETA. |
| `etsy_pipeline/models/job.py` | Central State Model | Shared state object passed between all workers. Stores theme metadata, parsed prompts, image paths, stage timestamps, and errors. |
| `etsy_pipeline/workers/` | Stage Workers | Autonomous python worker modules (`ImageWorker`, `BackgroundRemovalWorker`, `UpscaleWorker`, `MockupWorker`, `MetadataWorker`). |

---

## 🔄 End-to-End Pipeline Execution Lifecycle

### Step 1: Prompt File Injection & Job Initialization
1. Seller selects a prompt `.txt` file in the UI (fetched via `GET /api/v1/prompts/files`).
2. Seller clicks **Run Pipeline**. Frontend calls `POST /api/v1/pipeline/jobs` with:
   ```json
   {
     "theme_name": "Lilo & Stitch Birthday",
     "prompt_file_path": "gs://etsy-pipeline-bucket/Clipart/2026-07-28/Lilo_Stitch/Lilo_Stitch.txt"
   }
   ```
3. `PipelineRunnerService.create_job()` initializes `Job(job_id=..., theme=...)`:
   - Extracts `date_folder` from `prompt_file_path` (e.g. `Clipart/2026-07-22/`) so all generated assets stay in the original date directory rather than creating a new folder with today's date.
   - Downloads/reads text content from GCS (`gs://...`) or local disk (`output/Clipart/...`).
   - Uses `PromptWorker._parse_response(raw_text)` to parse section headings (`## MAIN_CHARACTER`, `## PATTERN`, etc.) into `job.prompts` and `job.character_roster`.
   - Excludes prompt generation from stage execution. Initializes 6 stages in `pending` state with total prompt count.

### Step 2: Sequential Worker Execution with 100% Module Resiliency
Before executing each worker stage, `PipelineRunnerService` checks if **100% of that stage's expected output files** already exist in storage (`_is_stage_100pct_complete`):
- For `image_gen`, `bg_removal`, `mockup_creation`: Checks local disk and GCS (`gs://bucket/Clipart/...`).
- For `upscaling`: Queries Google Drive folder `Clipart/main_data/<date_folder>/<theme_slug>/` under root folder `1JWUBqtP-PG-hRLEQj4Kh_vNzfb_G_PCP` as the exclusive source of truth. Local VM disk checks are bypassed to prevent false-positive stage skips from leftover files.
- `GoogleDriveService._get_credentials()` automatically resolves relative credential paths (`cred/token.json` and `cred/client_secret.json`) against `_PROJECT_ROOT` to prevent authentication failure across working directories.
- If 100% complete: The stage is marked `Completed ✅` immediately and worker execution is skipped.
- If incomplete / interrupted: The stage is marked `Pending ⏳` and runs cleanly from start.

To prevent blocking the FastAPI Uvicorn async event loop during heavy CUDA or subprocess operations, `PipelineRunnerService.run_full_pipeline_async` wraps `asyncio.to_thread` with `asyncio.create_task` (`worker_task = asyncio.create_task(asyncio.to_thread(cls._execute_stage_worker_sync, job, stage_name))`). This produces a true `asyncio.Task` object supporting `.done()` polling while progress metrics and ETA are continuously updated.

1. **Stage 1 — Image Generation (`image_gen`)**:
   - Worker: `ImageWorker.run(job)`
   - Submits each prompt to local ComfyUI server (`http://127.0.0.1:8188/prompt`).
   - Saves raw generated PNGs to `raw_images/misc_category/` and `raw_images/pattern_scene_bonus_category/`.
   - Uploads raw PNGs to GCS.

2. **Stage 2 — Background Removal (`bg_removal`)**:
   - Worker: `BackgroundRemovalWorker.run(job)`
   - Runs `rembg` (`isnet-general-use`) on `misc_category` images to output transparent PNGs in `no_bg/misc_category/`.
   - Direct-copies pattern/scene images to `no_bg/pattern_scene_bonus_category/`.
   - Uploads transparent PNGs to GCS & Google Drive raw_data folder.
   - **Storage Cleanup**: Purges `raw_images/` from both local VM disk and GCS post-stage to save cloud storage.

3. **Stage 3 — AI Upscaling (`upscaling`)**:
   - Worker: `UpscaleWorker.run(job)`
   - Upscales transparent PNGs using Real-ESRGAN `4x-UltraSharp` with dynamic tile scaling on CUDA OOM.
   - Standardizes output resolution to 4096px at 300 DPI.
   - Uploads upscaled files directly to Google Drive path (`Clipart/main_data/<date>/<theme_slug>`).
   - Purges local upscaled temporary folder after upload.

4. **Stage 4 & 5 — Mockup Creation & PDF Generation (`mockup_creation`, `pdf_generation`)**:
   - Worker: `MockupWorker.run(job)`
   - Executes `etsy mockup creator` subprocess to generate 4 high-resolution Etsy product mockups (`Hero.png`, grid mockups, style mockups).
   - Shares upscaled Google Drive folder publicly and retrieves share link.
   - Renders single-page A4 clickable PDF catalog wrapper (`<theme_slug>.pdf`) using ReportLab.
   - Uploads mockups and PDF wrapper to Google Drive (`Clipart/raw_data/<date>/<theme_slug>/mockups/`) and GCS.

5. **Stage 6 — Etsy Metadata Generation (`metadata_generation`)**:
   - Worker: `MetadataWorker.run(job)`
   - Synthesizes listing title (max 140 chars), 300 DPI listing description, and 13 Etsy SEO tags (max 20 chars each).
   - Stores metadata in `job.metadata`.

---

## 📊 Live Progress & Time Estimation (ETA) Calculation

During worker execution, `PipelineRunnerService` polls worker progress every 0.5 seconds:
- **Items Progress**: `images_done` / `images_total` (e.g. `14 / 24 items`).
- **Progress Percentage**: `progress_percent = (images_done / images_total) * 100`.
- **Elapsed Time**: `elapsed_seconds = (now - started_at).total_seconds()`.
- **ETA (Estimated Time Remaining)**:
  $$\text{ETA} = \left(\frac{\text{elapsed\_seconds}}{\text{images\_done}}\right) \times (\text{images\_total} - \text{images\_done})$$

Metrics are returned via `GET /api/v1/pipeline/jobs/{job_id}` and streamed over WebSocket (`/api/v1/pipeline/jobs/{job_id}/stream`).

---

## 🛡️ Error Handling & Single-Stage Retries

If a stage throws an exception (e.g., CUDA OOM or network timeout):
1. The worker catches the exception, marks the stage status as `failed`, and records the root error message in `error_message` and full traceback in `stderr_log`.
2. Execution halts without losing completed assets from previous stages.
3. Sellers can call `POST /api/v1/pipeline/jobs/{job_id}/stages/{stage_name}/retry`.
4. `PipelineRunnerService` resets the target stage to `pending`, clears error logs, and re-executes **only that specific stage**.
