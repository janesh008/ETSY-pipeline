# CONTEXT.md — `etsy_pipeline/` package

**Last reviewed:** 2026-07-19

## Responsibility
The core installable Python package containing all pipeline business logic: configuration, data models, orchestration, utilities, and per-stage workers.

## Not responsible for
CLI argument parsing (→ `scripts/`), test assertions (→ `tests/`), or the legacy Colab notebook code (→ `ETSY_main_colab/`).

## Public interface
- `etsy_pipeline.pipeline.orchestrator.Pipeline` — the single entry point consumers call
- `etsy_pipeline.models.job.Job` — the state object passed between all stages
- `etsy_pipeline.config.settings.get_settings()` — singleton config accessor

## Dependencies
- Subpackages are fully self-contained and import only from each other in a strict layering:
  `config` ← `models` ← `utils` ← `workers` ← `pipeline`
  (upper layers may import lower; lower layers never import upper)

## Gotchas / invariants
- **Layering is enforced by convention, not tooling.** If you add a `workers → pipeline` import, the orchestrator will silently create a circular dependency. Check `graph.json` edges after any new cross-package import.
- Every public function and class must have a Google-style docstring whose first line matches the `docstring_summary` field in `graph.json`. Keep them in sync.
- The `__init__.py` at this level exposes only `__version__`. Do not re-export workers or models here — callers import directly from submodules.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:**
  - [`config/CONTEXT.md`](config/CONTEXT.md)
  - [`models/CONTEXT.md`](models/CONTEXT.md)
  - [`pipeline/CONTEXT.md`](pipeline/CONTEXT.md)
  - [`utils/CONTEXT.md`](utils/CONTEXT.md)
  - [`workers/CONTEXT.md`](workers/CONTEXT.md)
