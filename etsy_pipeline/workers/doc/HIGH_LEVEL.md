# High-Level Responsibilities — `workers`

This subpackage houses the actual processing logic for all stages of the pipeline. Each stage is run by a dedicated worker.

## What it is responsible for
*   Calling external APIs (like Google Gemini) and processing their outputs.
*   Formatting user prompts and validating generated responses against locked schema constraints.
*   Exposing exactly one public method: `run(job: Job) -> Job`.

## What it is NOT responsible for
*   Sequencing or orchestrating execution order (handled by `pipeline/`).
*   Worker-to-worker direct calling. A worker is completely self-contained and isolated.
