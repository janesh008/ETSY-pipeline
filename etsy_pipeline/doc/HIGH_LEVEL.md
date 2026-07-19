# High-Level Responsibilities — `etsy_pipeline/`

This folder contains the core Python package containing all pipeline logic (orchestration, configuration, data models, utility infrastructure, and individual stage workers).

## What it is responsible for
*   Housing the entire pipeline code structured under layered subpackages (`config`, `models`, `pipeline`, `utils`, `workers`).
*   Defining self-contained resource templates inside `resources/` for Gemini generation.

## What it is NOT responsible for
*   CLI argument parsing and display (this is handled by `scripts/`).
*   Direct script execution or automation hooks.
