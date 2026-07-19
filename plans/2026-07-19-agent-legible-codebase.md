# Plan: Agent-Legible Codebase — Living Docs + Code Graph

**Date:** 2026-07-19
**Status:** done
**Related:** [CONTEXT.md](../CONTEXT.md), [etsy_pipeline/CONTEXT.md](../etsy_pipeline/CONTEXT.md)

---

## Problem
The `etsy_pipeline` codebase was structurally sound but opaque to a cold-start agent or new engineer, requiring full source re-embedding every session. Two changes fix this: a lightweight CONTEXT.md at every folder level (cheap text reads), and a static AST code graph (single JSON read for structural context).

---

## Clarifying questions & answers
- Q: Graph staleness: hard-fail or auto-regenerate in pre-commit?
  A: Auto-regenerate (option b) — better developer experience, analogous to lockfile behavior.
- Q: Call-edge depth: module-level or function-level?
  A: Function-level (option b) — more useful for agent "what calls what" queries.
- Q: mypy strictness on existing code?
  A: Warn-only initially (option b) — non-blocking; tighten per future workstream.

---

## Approach
Added three layers simultaneously:
1. **CONTEXT.md hierarchy** (9 files) — human-authored, <200 words each, strict 6-section template. Written as senior-engineer onboarding notes, not docstring dumps.
2. **`scripts/build_graph.py`** — stdlib `ast` walker. Extracts module/class/function nodes (with docstring summaries and signatures) and import/call edges. Outputs `.repo-graph/graph.json`. Supports `--check` for CI.
3. **Tooling** — `ruff` (lint+format), `mypy` (warn-only), `pre-commit` hooks. Config in `pyproject.toml`.
4. **`AGENTS.md`** — single cross-tool workflow file with the Plan-Before-Code rule and navigation guide.

**Alternatives considered:**
- tree-sitter for graph generation — rejected because stdlib `ast` is sufficient for this codebase and adds zero dependencies.
- Separate CLAUDE.md and Cursor rules files — rejected because `AGENTS.md` is now the cross-tool standard (Antigravity, Codex, Claude Code all read it).
- GraphML format for the graph — rejected because JSON is more agent-friendly (no XML parser needed).

---

## Scope

**Files/modules created:**
- `CONTEXT.md` — repo root context
- `AGENTS.md` — cross-tool workflow rules
- `plans/_template.md` — plan file template
- `plans/2026-07-19-agent-legible-codebase.md` — this plan
- `etsy_pipeline/CONTEXT.md` — package context
- `etsy_pipeline/config/CONTEXT.md` — config subpackage
- `etsy_pipeline/models/CONTEXT.md` — models subpackage
- `etsy_pipeline/pipeline/CONTEXT.md` — pipeline subpackage
- `etsy_pipeline/utils/CONTEXT.md` — utils subpackage
- `etsy_pipeline/workers/CONTEXT.md` — workers subpackage
- `scripts/CONTEXT.md` — scripts context
- `tests/CONTEXT.md` — tests context
- `scripts/build_graph.py` — AST graph generator
- `.repo-graph/graph.json` — generated code graph (committed)
- `.pre-commit-config.yaml` — pre-commit hook config

**Files/modules modified:**
- `pyproject.toml` — added `[tool.ruff]`, `[tool.mypy]`; added ruff, mypy, pre-commit to dev deps
- `.gitignore` — track `.repo-graph/`, ignore tool caches

**Out of scope:** Fixing existing mypy type errors (separate task). Adding type hints to files that lack them. Modifying any business logic. CI/CD pipeline (pre-commit covers local).

---

## Risks & edge cases
- AST call-edge detection is static only — dynamic dispatch is invisible. Documented in `build_graph.py` header and graph schema (`"static_only": true`).
- CONTEXT.md files will go stale as code evolves. Mitigated by `Last reviewed:` date and the convention that each CONTEXT.md update is part of the same PR as the code change.
- ruff/mypy may surface pre-existing issues in existing files. Mypy is warn-only; ruff `--fix` is safe for auto-fixable issues.

---

## Steps (completed in order)
1. Updated `pyproject.toml` with ruff, mypy, pre-commit config
2. Wrote `scripts/build_graph.py` — AST walker + JSON emitter
3. Generated `.repo-graph/graph.json` (123 nodes, 386 edges)
4. Wrote all 9 CONTEXT.md files (root → package → subpackage)
5. Wrote `AGENTS.md` (workflow + navigation guide)
6. Wrote `plans/_template.md` and this plan file
7. Wrote `.pre-commit-config.yaml`
8. Updated `.gitignore`
9. Installed pre-commit and ran hooks

---

## Rollback
All changes are additive (new files) except `pyproject.toml` and `.gitignore`. Revert those two files with `git checkout HEAD pyproject.toml .gitignore`. Delete `.repo-graph/`, `CONTEXT.md` files, `AGENTS.md`, `plans/`, and `.pre-commit-config.yaml`. Run `pre-commit uninstall`.
