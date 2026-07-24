# AGENTS.md

This file is read natively by Antigravity, Codex, and Claude Code (no CLAUDE.md needed — Claude reads AGENTS.md when CLAUDE.md is absent). Keep it lean: process here, per-feature detail in `plans/`.

---

## Navigating this repo (read first)

Before writing or searching code, orient yourself with these two cheap reads:

1. **[`.repo-graph/graph.json`](.repo-graph/graph.json)** — machine-readable structural map (123 nodes, 386 edges as of last generation). Keys to look for: `nodes[].id`, `nodes[].docstring_summary`, `edges[].kind` (`"import"` or `"call"`). This tells you what calls what without opening any source file.

2. **Hierarchical Living Documentation (`doc/` subfolders)** — Walk the project top-down using non-technical and technical guides:
   - [Root Project Map (`doc/MASTER_MAP.md`)](file:///d:/Janesh/ETSY/ETSY-pipeline/doc/MASTER_MAP.md) — Walkthrough of the entire pipeline with clickable links to all files.
   - [Technical Architecture (`doc/ARCHITECTURE.md`)](file:///d:/Janesh/ETSY/ETSY-pipeline/doc/ARCHITECTURE.md) — Technical layouts and GCP designs.
   - Every folder has a `doc/` subdirectory containing `HIGH_LEVEL.md`, `SKILL.md`, and `DETAILED.md` describing that directory's scope, coding rules, and detailed behaviors. Refer to these to solve features or bugs.

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

6. **Git Pushes:** Committing files locally to track progress is allowed. However, **never run `git push`** to the remote repository (GitHub) automatically. Only push the code to GitHub when the user explicitly requests it in their message.

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

## Software Development Principles (Karpathy Guidelines)

Guidelines to eliminate common LLM coding mistakes and enforce senior engineering discipline:

### 1. Think Before Coding
- **Don't assume. Don't hide confusion. Surface tradeoffs.**
- State assumptions explicitly before implementing. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.

### 2. Simplicity First
- **Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked. No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- If you write 200 lines and it could be 50, rewrite it.
- Ask: *"Would a senior engineer say this is overcomplicated?"* If yes, simplify.

### 3. Surgical Changes
- **Touch only what you must. Clean up only your own mess.**
- When editing existing code, don't "improve" adjacent code, comments, or formatting.
- Match existing style. Every changed line must trace directly to the user's request.
- Remove imports/variables/functions that YOUR changes made unused.

### 4. Goal-Driven Execution
- **Define success criteria. Loop until verified.**
- Transform tasks into verifiable goals (`1. [Step] → verify: [check]`).
- Write tests or verification checks before declaring completion.

---

## Past plans

See [`plans/`](plans/) for all implementation decisions. Read relevant plans before modifying a feature — they explain *why* choices were made, not just *what* was built.
