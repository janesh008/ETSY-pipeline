# CONTEXT.md — `etsy_pipeline/config/`

**Last reviewed:** 2026-07-19

## Responsibility
Centralises all runtime configuration: loads values from environment variables and `.env`, validates types, and exposes a singleton `Settings` instance. No business logic lives here.

## Not responsible for
Secrets management or rotation. Validating that external services (Vertex AI, ComfyUI) are reachable — that belongs in each worker's `__init__` or health-check method.

## Public interface
```python
from etsy_pipeline.config.settings import get_settings, Settings

settings = get_settings()          # singleton — cached via @lru_cache
settings.gemini_model              # "gemini-2.5-flash"
settings.use_vertex_ai             # True / False
settings.skill_file_path           # absolute path to SKILL.md
```

## Dependencies
- `pydantic-settings` — `BaseSettings` for env-var loading and validation
- `pydantic` — `Field` for metadata and defaults
- No imports from other `etsy_pipeline` subpackages (this is the lowest layer)

## Gotchas / invariants
- `get_settings()` is cached with `@lru_cache(maxsize=1)`. To reload (e.g., in tests that patch env vars), call `get_settings.cache_clear()` first.
- `USE_VERTEX_AI=True` enables ADC auth; `USE_VERTEX_AI=False` requires `GOOGLE_API_KEY`. Both paths are live — test both when changing auth logic.
- `skill_file_path` and `metadata_skill_file_path` default to package-internal paths inside `etsy_pipeline/resources/` (making the package fully self-contained). If they need to be overridden (e.g. to use a custom prompt file), set `SKILL_FILE_PATH` or `METADATA_SKILL_FILE_PATH` in the `.env` file.
- Adding a new config field: add it to `Settings`, add it to `.env.example`, and document it in the root `CONTEXT.md` if it affects developer setup.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:** (no subdirectories)
- **Key file:** [`settings.py`](settings.py)
