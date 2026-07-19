# CONTEXT.md — `etsy_pipeline/pipeline/`

**Last reviewed:** 2026-07-19

## Responsibility
Sequences worker execution in dependency order, handles per-stage error catching and `Job` status transitions, and provides the single `Pipeline.run(job)` method that external callers (CLI, FastAPI) use.

## Not responsible for
Any business logic — no prompt parsing, no API calls, no file I/O. If you find business logic here, it belongs in a worker. The pipeline contains only orchestration.

## Public interface
```python
from etsy_pipeline.pipeline.orchestrator import Pipeline

pipeline = Pipeline()
job = pipeline.run(job)          # full pipeline
job = pipeline.run_stage(job, "prompt_generation")  # single stage (re-run / debug)
```

## Dependencies
- `etsy_pipeline.config.settings` — settings passed down to workers
- `etsy_pipeline.models.job` — `Job`, `JobStatus`
- `etsy_pipeline.utils.exceptions` — `PipelineError` (caught here, not re-raised)
- `etsy_pipeline.utils.logging` — `get_logger`, `setup_logging`
- `etsy_pipeline.workers.prompt_worker` — `PromptWorker` (and future workers)

## Gotchas / invariants
- **Worker instances are created once at `Pipeline.__init__`** and reused across `run()` calls. Workers must be stateless across jobs — if a worker caches job-specific state on `self`, it will leak between runs. The Gemini client cache on `PromptWorker._client` is safe (it's auth-state, not job-state).
- **Stage execution order is defined in the `stages` list inside `run()`** — it is a plain Python list, not derived from a dependency graph. If you add a worker, add it to both the list and the `worker_map` in `run_stage()`.
- When a stage raises `PipelineError`, the pipeline calls `stage.mark_failed()`, sets `job.status = FAILED`, and breaks. Subsequent stages do not run. This is intentional — stages are sequential and dependent.
- **Future FastAPI wiring:** `Pipeline` is designed to be a long-lived singleton injected as a dependency, not instantiated per request.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:** (no subdirectories)
- **Key file:** [`orchestrator.py`](orchestrator.py)
