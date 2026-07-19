# AGENTS.md

This file is read natively by Antigravity, Codex, and Claude Code (no CLAUDE.md needed — Claude reads AGENTS.md when CLAUDE.md is absent). Keep it lean: process here, per-feature detail in `plans/`.

---

## Navigating this repo (read first)

Before writing or searching code, orient yourself with these two cheap reads:

1. **[`.repo-graph/graph.json`](.repo-graph/graph.json)** — machine-readable structural map (123 nodes, 386 edges as of last generation). Keys to look for: `nodes[].id`, `nodes[].docstring_summary`, `edges[].kind` (`"import"` or `"call"`). This tells you what calls what without opening any source file.

2. **CONTEXT.md tree** — human-written onboarding notes at every folder level. Walk it top-down:
   - [`CONTEXT.md`](CONTEXT.md) → [`etsy_pipeline/CONTEXT.md`](etsy_pipeline/CONTEXT.md)
   - → [`config/`](etsy_pipeline/config/CONTEXT.md) | [`models/`](etsy_pipeline/models/CONTEXT.md) | [`pipeline/`](etsy_pipeline/pipeline/CONTEXT.md) | [`utils/`](etsy_pipeline/utils/CONTEXT.md) | [`workers/`](etsy_pipeline/workers/CONTEXT.md)
   - → [`scripts/CONTEXT.md`](scripts/CONTEXT.md) | [`tests/CONTEXT.md`](tests/CONTEXT.md)

Only open full source files for the specific nodes you actually need to change.

---

## Development Workflow — Plan Before Code

Before writing or modifying any code, follow this sequence for every feature request, new module, or bug fix:

1. **Analyze first.** Read the request against the existing CONTEXT.md files and `.repo-graph/graph.json` before responding. Do not start planning until you understand what already exists and what would be affected.

2. **Ask before assuming.** If the request is ambiguous or has real design tradeoffs, ask targeted clarifying questions — the way a senior engineer scoping work would, not a generic checklist. Cover things like: expected scale/failure modes, backward compatibility, which existing module owns this responsibility, and whether this is a one-off or a pattern that will repeat. Skip questions whose answers are already inferable from the codebase or the request itself.

3. **Propose a plan, not code.** Once the approach is clear, write an implementation plan and stop — do not write code yet. The plan must include:
   - Problem statement (1–2 sentences)
   - Proposed approach and why (including any rejected alternatives)
   - Files/modules to be created or touched
   - Risks, edge cases, and rollback consideration
   - Ordered implementation steps

4. **Wait for explicit approval.** Do not proceed to implementation until the user confirms the plan.

5. **Save the plan, then implement.** On approval, save the plan as a Markdown file at `plans/YYYY-MM-DD-<short-slug>.md` (see [`plans/_template.md`](plans/_template.md)) *before* writing any code. Only then begin implementation, following the saved plan. If the approach changes mid-implementation, update the plan file to match — it should always reflect what was actually built, not just what was intended.

This applies regardless of which agent is executing — plan files are plain Markdown with no tool-specific syntax, so any agent can read past plans for context on prior decisions.

---

## Coding standards

- **PEP 8 + Google-style docstrings** on every public function/class. The docstring first line feeds directly into `graph.json`'s `docstring_summary` field — keep the two in sync intentionally.
- **Full type hints** with `from __future__ import annotations` on every module.
- **Linting/formatting:** `ruff` (Black-compatible, configured in `pyproject.toml`). Run `ruff check . --fix && ruff format .` before committing.
- **Type checking:** `mypy etsy_pipeline` (warn-only mode; config in `pyproject.toml`).
- **No `print()`** — use `get_logger(__name__)` from `etsy_pipeline.utils.logging`.
- **No hardcoded values** — all config lives in `etsy_pipeline/config/settings.py`.
- Every module's top-level docstring first line must match the "Responsibility" field in its parent `CONTEXT.md`.

---

## Layering rule

Imports must flow strictly upward:

```
config  ←  models  ←  utils  ←  workers  ←  pipeline  ←  scripts
```

A lower layer (e.g. `models`) must never import from a higher layer (e.g. `workers`). Verify with `graph.json` edge direction after any new cross-package import.

---

## Adding a new pipeline stage (checklist)

When adding a future worker (ImageWorker, BackgroundRemovalWorker, etc.):

1. Add the exception class to `etsy_pipeline/utils/exceptions.py`
2. Add the stage name and `StageResult()` to `Job.stages` in `etsy_pipeline/models/job.py`
3. Create `etsy_pipeline/workers/<stage>_worker.py` with a `<Stage>Worker` class exposing `run(job: Job) -> Job`
4. Create `etsy_pipeline/workers/<stage>_worker_config.py` for stage-specific constants
5. Wire the worker into `pipeline/orchestrator.py` (both `stages` list and `worker_map`)
6. Add `tests/test_<stage>_worker.py`
7. Update `etsy_pipeline/workers/CONTEXT.md` worker table
8. Regenerate graph: `python scripts/build_graph.py`

---

## Past plans

See [`plans/`](plans/) for all implementation decisions. Read relevant plans before modifying a feature — they explain *why* choices were made, not just *what* was built.
