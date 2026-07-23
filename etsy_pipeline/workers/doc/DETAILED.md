# Code Details — `workers`

## Directory Structure & Documentation Subfolders

The `etsy_pipeline/workers/doc/` directory is structured as follows:

*   **[`main_modules/`](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/main_modules/)**: Documentation for primary pipeline worker modules.
    *   [📄 remove_bg.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/main_modules/remove_bg.md)
    *   [📄 upscale.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/main_modules/upscale.md)
    *   [📄 mockups.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/main_modules/mockups.md)
    *   [📄 metadata.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/main_modules/metadata.md)
    *   [📄 etsy_upload.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/main_modules/etsy_upload.md)
*   **[`new_features/`](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/new_features/)**: Feature design specifications and implementation plans.
    *   [📄 implementation_plan_etsy-listing-metadata.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/new_features/implementation_plan_etsy-listing-metadata.md)
    *   [📄 implementation_plan_vm_first_storage_and_cleanup.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/new_features/implementation_plan_vm_first_storage_and_cleanup.md)
*   **[`bug_resolvers/`](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/bug_resolvers/)**: Diagnostic reports and resolution documentation for pipeline bugs.
    *   [📄 bug_resolver_missing_mockups.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/bug_resolvers/bug_resolver_missing_mockups.md)
    *   [📄 bug_resolver_mockup_path_resolution_error.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/doc/bug_resolvers/bug_resolver_mockup_path_resolution_error.md)

---

## Code Behavior

This subpackage contains:
*   [📄 prompt_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/prompt_worker.py) — Stage 1 worker.
*   [📄 prompt_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/prompt_worker_config.py) — Configuration and templates.
*   [📄 image_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/image_worker.py) — Stage 2 worker (ComfyUI GPU Image Generation).
*   [📄 image_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/image_worker_config.py) — ComfyUI endpoints and node constants.
*   [📄 bg_removal_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/bg_removal_worker.py) — Stage 3 worker (rembg Background Removal).
*   [📄 bg_removal_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/bg_removal_worker_config.py) — Background removal model and category folder constants.
*   [📄 upscale_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/upscale_worker.py) — Stage 4 worker (Real-ESRGAN AI Upscaling).
*   [📄 upscale_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/upscale_worker_config.py) — Upscaling configuration and GDrive folders.

### `PromptWorker` Class Flow
1.  **Entry (`run(job)`):** Checks if prompts are already generated. If not, sets stage status to running, resolves the Gemini client, builds the user prompt, sends it to Gemini, parses the output, validates it, and saves it back to the `Job`.
2.  **Resource Loading (`_load_skill_file()`):** Loads [SKILL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources/SKILL.md) at runtime, strips YAML frontmatter, and passes the text as Gemini's `system_instruction`.
3.  **Client Initialization (`_get_client()`):** Supports double auth. If `USE_VERTEX_AI=True`, instantiates the client with `vertexai=True` using GCP Application Default Credentials. Otherwise, initializes with `api_key=google_api_key`.
4.  **Response Parsing (`_parse_response()`):** Uses regex to split Gemini's markdown response into locked sections based on headings (e.g. `## MAIN_CHARACTER`).
5.  **Roster Extraction (`_extract_roster()`):** Parses character name mappings and lists them in `job.character_roster`.
6.  **Validation (`_validate_prompts()`):** Enforces rules (e.g., at least one section must be populated, active sections must have at least 10 prompts, missing sections are added as empty lists).

### `ImageWorker` Class Flow
1.  **Entry (`run(job)`):** Connects to local ComfyUI API on port 8188. Iterates through all job prompts.
2.  **Workflow Injection (`_inject_prompt()`):** Loads `image_z_image_turbo1.json` API template, injects text prompt into node `57:27`, sets random seed on node `57:3`.
3.  **Generation & Poll:** Posts prompt to `/prompt`, polls `/history` until completed, downloads resulting PNG.
4.  **Naming & Storage:** Saves image locally as `{theme_slug}_{section}_{sec_count:03d}.png` under `misc_category/` or `pattern_scene_bonus_category/`, uploads to GCS, and pushes progress to MongoDB.

### `BackgroundRemovalWorker` Class Flow
1.  **Entry (`run(job)`):** Resolves `raw_images/` inputs locally or downloads from GCS fallback.
2.  **Category Partitioning:** Scans `misc_category` and `pattern_scene_bonus_category`.
3.  **AI Removal:** Uses `rembg` (`isnet-general-use`) to remove backgrounds from `misc_category` images and outputs transparent PNGs to `no_bg/misc_category/`.
4.  **Direct Copy:** Copies `pattern_scene_bonus_category` images directly to `no_bg/pattern_scene_bonus_category/` without AI processing.
5.  **Cloud Sync & Cleanup:** Uploads all `no_bg/` PNGs to BOTH GCS and Google Drive, then purges `raw_images/` from both local VM disk and GCS to conserve storage.

### `UpscaleWorker` Class Flow
1.  **Entry (`run(job)`):** Resolves `no_bg/` inputs locally or downloads from GCS/Drive fallbacks.
2.  **Model Loading:** Standardizes 4x-UltraSharp weights setup.
3.  **Enhancement & Tiling:** Runs `RealESRGANer` with dynamic tile sizing fallback (`512` → `256` → `128` on CUDA OOM).
4.  **Standardization:** Resizes the upscaled image to exactly 4096px on its longest side at 300 DPI.
5.  **Direct GDrive Delivery:** Delivers all upscaled PNGs directly to Google Drive under `Clipart/main_data/<date>/<theme_slug>/`. Cleans up local upscaled directory post-upload.
