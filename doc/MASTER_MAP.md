# Etsy Pipeline — Master Project Map

Welcome! This document is a non-technical, friendly guide designed to help anyone (whether you are an AI agent, a developer, or a non-technical team member) understand exactly how this project works, what each part does, and how to make changes or solve bugs.

---

## 🗺️ Visual Project Map & Clickable Links

Use these links to jump directly to any directory or file in the codebase:

*   [**📁 Project Root Directory**](file:///d:/Janesh/ETSY/ETSY-pipeline)
    *   [📄 pyproject.toml](file:///d:/Janesh/ETSY/ETSY-pipeline/pyproject.toml) — Project dependencies and tool settings.
    *   [📄 AGENTS.md](file:///d:/Janesh/ETSY/ETSY-pipeline/AGENTS.md) — Workflow instructions for AI coding assistants.
    *   [📄 README.md](file:///d:/Janesh/ETSY/ETSY-pipeline/README.md) — Main GitHub setup guide.
    *   [**📁 Core Package (`etsy_pipeline`)**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline)
        *   [📄 __init__.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/__init__.py) — Package entry point.
        *   [**📁 config/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/config) — System settings and env-var validation.
            *   [📄 settings.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/config/settings.py) — Configuration schema.
        *   [**📁 models/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/models) — Shared data structures.
            *   [📄 job.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/models/job.py) — Pydantic Job state model.
        *   [**📁 pipeline/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/pipeline) — Execution workflow sequencer.
            *   [📄 orchestrator.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/pipeline/orchestrator.py) — Orchestrator class.
        *   [**📁 resources/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources) — Copied prompt templates.
            *   [📄 SKILL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources/SKILL.md) — Image prompt generator system prompt.
            *   [📄 ETSY-Listing-Master-Prompt.txt](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources/ETSY-Listing-Master-Prompt.txt) — SEO listing system prompt.
        *   [**📁 utils/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/utils) — Logging and exception handlers.
            *   [📄 exceptions.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/utils/exceptions.py) — Custom pipeline errors.
            *   [📄 logging.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/utils/logging.py) — Colored console & cloud JSON logger.
        *   [**📁 workers/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers) — Pipeline stage implementations.
            *   [📄 prompt_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/prompt_worker.py) — Clipart prompt generation.
            *   [📄 prompt_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/prompt_worker_config.py) — Rules for prompt parsing.
            *   [📄 image_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/image_worker.py) — GPU image generation via ComfyUI.
            *   [📄 image_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/image_worker_config.py) — ComfyUI node constants.
            *   [📄 bg_removal_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/bg_removal_worker.py) — AI background removal via rembg.
            *   [📄 bg_removal_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/bg_removal_worker_config.py) — Background removal constants.
    *   [**📁 scripts/**](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts) — Runnable CLI commands.
        *   [📄 run_prompts.py](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts/run_prompts.py) — CLI command to run prompt stage.
        *   [📄 run_image_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts/run_image_worker.py) — CLI runner for image generation daemon.
        *   [📄 run_bg_removal_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts/run_bg_removal_worker.py) — CLI runner for background removal daemon.
        *   [📄 build_graph.py](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts/build_graph.py) — Code graph generator.
    *   [**📁 tests/**](file:///d:/Janesh/ETSY/ETSY-pipeline/tests) — Automated test suite.
        *   [📄 test_prompt_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/tests/test_prompt_worker.py) — Unit/Integration tests.

---

## 💡 What does this project do? (The High-Level Flow)

This project is a pipeline designed to create digital clipart bundles and automatically list them on Etsy. Think of it like an assembly line:

1.  **Input:** You give the pipeline a **Theme** (like "Lilo & Stitch") and an **Event** (like "birthday").
2.  **Prompt Gen (Gemini):** The pipeline asks the Gemini AI to write image generation prompts. It splits these prompts into sections (Main Character, Secondary Characters, Patterns, Props, and Scenes).
3.  **Image Gen (ComfyUI - Future):** A graphics engine renders these prompts into actual clipart pictures.
4.  **BG Removal (Future):** A background remover strips the white backgrounds so they become transparent PNGs.
5.  **Upscale (Future):** The images are made larger and crisp for professional printing.
6.  **Mockups (Future):** The pipeline places the clipart onto digital boxes and paper frames so customers can see what they look like.
7.  **SEO Metadata (Gemini - Future):** Gemini writes an optimized Etsy listing description, title, and 13 tags.
8.  **CSV (Future):** The files and text are organized into a bulk CSV spreadsheet.
9.  **Etsy Upload (Future):** The pipeline pushes the listings directly onto Etsy.

---

## 🤖 What do the "Agents" and "Workers" do?

*   **Workers:** Each step on the assembly line is run by a **Worker**. For example, the `PromptWorker` handles step 2. Workers are stateless; they only do the work they are asked to do on a specific job, then they pass the job along.
*   **Agents (Future):** In the future, we will wrap these workers in intelligent **AI Agents**. An agent will monitor the worker, decide if the outputs look high quality, or automatically run corrections if a step fails.
*   **Job Object:** All workers read from and write to a single Pydantic **Job** state model. The job carries the configuration (e.g. theme) and collects the outputs (e.g. prompt lists, files) as they are created.

---

## 🛠️ How to develop a feature or resolve a bug

If you are tasked with fixing a bug or adding a feature, follow this simple non-technical loop:

1.  **Look up the target folder:** Find the folder you want to change in the [Visual Project Map](#-visual-project-map-clickable-links) and click on its link.
2.  **Open its `doc/` folder:** Every folder has a `doc/` subdirectory.
    *   Read **`HIGH_LEVEL.md`** to understand what that folder is responsible for.
    *   Read **`SKILL.md`** to know the coding rules, Gotchas, and instructions for that folder.
    *   Read **`DETAILED.md`** to see how the code is structured and what it does.
3.  **Create a Plan:** Write down your proposed changes in `plans/` using the plan template.
4.  **Implement & Test:** Make the code edits, run `ruff format . && ruff check . --fix` to format the code, and run tests via `pytest tests/ -v -k "not integration"` to verify everything works.
5.  **Regenerate Code Graph:** Run `python scripts/build_graph.py` to ensure the project code graph is updated.
