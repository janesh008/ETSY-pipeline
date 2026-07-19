# CONTEXT.md — `etsy_pipeline/models/`

**Last reviewed:** 2026-07-19

## Responsibility
Defines the shared data models (Pydantic) that carry state between pipeline stages. The `Job` model is the single source of truth for everything a pipeline run produces or consumes.

## Not responsible for
Persistence (saving/loading Jobs to disk or a database), business logic, or validation of external API responses — each worker owns that.

## Public interface
```python
from etsy_pipeline.models.job import Job, JobStatus, StageResult, StageStatus

job = Job(theme="Lilo & Stitch", event_type="birthday")
job.status                     # JobStatus.PENDING
job.stages["prompt_generation"]  # StageResult(status=PENDING, ...)
job.prompts                    # dict[str, list[str]] — section → prompts
job.total_prompt_count         # computed property
job.add_log("message")         # append timestamped log entry
job.add_error("message")       # record error + log it
job.get_output_dir(root)       # Path for this job's output files
job.to_summary()               # human-readable status string
```

## Dependencies
- `pydantic` — model validation and serialization
- `uuid`, `datetime` (stdlib) — ID generation and timestamps
- No imports from other `etsy_pipeline` subpackages

## Gotchas / invariants
- **`Job` is mutable** — workers receive it, mutate it in place (calling `mark_running`, `mark_completed`, `add_log`), and return it. The Pipeline orchestrator does not deep-copy between stages.
- **`stages` dict keys are fixed** — they are defined at `Job` initialisation as the 8 known pipeline stage names. Do not add ad-hoc keys; add a new named stage or use `Job.logs` for ephemeral messages.
- **`event_type` default is `"Normal"`** — changed from `"birthday"` per user edit on 2026-07-18. Tests that assert on the default need updating if this changes again.
- When adding a new stage output field (e.g. `pdf_path`), add a corresponding `StageResult` entry in the `stages` default factory.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:** (no subdirectories)
- **Key file:** [`job.py`](job.py)
