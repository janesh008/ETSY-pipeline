# CONTEXT.md — `etsy_pipeline/utils/`

**Last reviewed:** 2026-07-19

## Responsibility
Shared infrastructure used by every other subpackage: structured logging setup, and the full exception hierarchy. No business logic; no imports from workers or pipeline.

## Not responsible for
Log shipping to GCP Cloud Logging (that happens automatically when the process runs on a Compute Engine instance with the Ops Agent — no code change needed). Exception recovery logic — that belongs in the orchestrator or the worker that raises.

## Public interface
```python
# Logging
from etsy_pipeline.utils.logging import get_logger, setup_logging
logger = get_logger(__name__)
setup_logging(level="INFO", log_format="console")  # call once at startup

# Exceptions
from etsy_pipeline.utils.exceptions import (
    PipelineError,          # base — catch this to catch all pipeline errors
    PromptGenerationError,  # stage-specific
    PromptParsingError,     # sub-class of PromptGenerationError
    PromptValidationError,  # sub-class of PromptGenerationError
    ConfigurationError,     # bad env/settings
    SkillFileError,         # SKILL.md missing or unreadable
    # ... ImageGenerationError, BackgroundRemovalError, etc.
)
```

## Dependencies
- `logging`, `json`, `sys`, `datetime` (stdlib only — zero third-party deps)

## Gotchas / invariants
- **Call `setup_logging()` exactly once** at process startup (CLI `main()` or FastAPI lifespan). Calling it multiple times adds duplicate handlers to the root logger and doubles every log line.
- **Log format is controlled by `log_format` setting** (`"console"` vs `"json"`). Never use `print()` anywhere in the codebase — it bypasses structured logging and breaks log parsing in GCP.
- **Exception hierarchy is intentional**: catch `PipelineError` in the orchestrator to handle all pipeline failures; catch a specific subclass (e.g. `PromptParsingError`) only when you can meaningfully recover from that exact failure type.
- When adding a new pipeline stage, add its exception class here first, then add the `stages` entry in `models/job.py`, then write the worker. This order avoids circular-import issues.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:** (no subdirectories)
- **Key files:** [`logging.py`](logging.py), [`exceptions.py`](exceptions.py)
