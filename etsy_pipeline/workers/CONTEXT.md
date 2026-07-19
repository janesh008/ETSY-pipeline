# CONTEXT.md — `etsy_pipeline/workers/`

**Last reviewed:** 2026-07-19

## Responsibility
One file per pipeline stage. Each worker contains all implementation for that stage and exposes exactly one public entry point: `run(job: Job) -> Job`. Workers are the only place where external APIs, disk I/O, and stage-specific logic live.

## Not responsible for
Sequencing (→ `pipeline/`), logging setup (→ `utils/logging`), or the `Job` model definition (→ `models/`). A worker must never call another worker directly.

## Public interface — current workers

| Worker | Entry point | Stage name in Job |
|--------|-------------|------------------|
| `PromptWorker` | `run(job) -> Job` | `"prompt_generation"` |
| *(future)* `ImageWorker` | `run(job) -> Job` | `"image_generation"` |
| *(future)* `BackgroundRemovalWorker` | `run(job) -> Job` | `"bg_removal"` |
| *(future)* `UpscaleWorker` | `run(job) -> Job` | `"upscaling"` |
| *(future)* `MockupWorker` | `run(job) -> Job` | `"mockups"` |
| *(future)* `MetadataWorker` | `run(job) -> Job` | `"metadata_generation"` |
| *(future)* `CSVWorker` | `run(job) -> Job` | `"csv_generation"` |
| *(future)* `EtsyWorker` | `run(job) -> Job` | `"etsy_upload"` |

Module-level entry: `generate_prompts(job: Job) -> Job` (thin wrapper, kept for future agent wrapping).

## Dependencies
- `etsy_pipeline.config.settings` — `get_settings()`, `Settings`
- `etsy_pipeline.models.job` — `Job`
- `etsy_pipeline.utils.exceptions` — stage-specific error classes
- `etsy_pipeline.utils.logging` — `get_logger`
- `google-genai` — Gemini API client (prompt and metadata workers)
- `prompt_worker_config.py` — constants derived from SKILL.md (locked sections, distributions, templates)

## Gotchas / invariants
- **Workers must be stateless across jobs.** Caching the Gemini client (`self._client`) is fine (it's auth state). Caching any `Job`-derived data on `self` is a bug — it will leak to the next job if the `Pipeline` reuses the worker instance.
- **The `run()` method must call `stage.mark_running()` at the top and either `mark_completed()` or `mark_failed()` before returning or raising.** The orchestrator depends on this to set `job.status` correctly.
- **Future agent wrapping pattern:** each worker class becomes the body of an agent's `execute()` method — the class interface is the agent contract, so don't change method signatures without updating the agent stub.
- When adding a new worker: (1) add exception to `utils/exceptions.py`, (2) add stage to `Job.stages` default factory in `models/job.py`, (3) write the worker here, (4) wire it into `pipeline/orchestrator.py`.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:** (no subdirectories)
- **Key files:** [`prompt_worker.py`](prompt_worker.py), [`prompt_worker_config.py`](prompt_worker_config.py)
