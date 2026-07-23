# Plan: Fix Hero Mockup Center Text Theme Name Interpolation

**Date:** 2026-07-24
**Status:** approved
**Related:** [etsy_pipeline/workers/CONTEXT.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/CONTEXT.md)

---

## Problem
In mockup creation, `Hero.png` center text `{theme_name_title}` renders as `"No Bg"` instead of the actual theme name (or slug). This occurs because `etsy mockup creator` receives `theme_dir` pointing to `.../no_bg` and doesn't match `"no_bg"` in its known subfolder fallback check tuple.

---

## Approach
Implement a two-layered defense:
1. Update `generator.py` and `server.py` in `etsy mockup creator` so subfolder detection includes `"no_bg"`, `"no bg"`, `"no-bg"`, `"nobg"`. When `theme_dir` is a `no_bg` folder, fall back to its parent folder name (`<theme_slug>`) and clean it up (removing trailing numbers and converting underscores to spaces).
2. Add `--theme-name` CLI option to `main.py` and accept `theme_name` parameter in `Generator.generate_all()`. Update `mockup_worker.py` in `etsy_pipeline` to pass `--theme-name` explicitly using `job.theme` (or fallback to `job.theme_slug.replace("_", " ")`).

**Alternatives considered:**
- Only pass `--theme-name` via CLI — rejected because standalone usage of `etsy mockup creator` on `no_bg` folders would still default to `"No Bg"`. Both mechanisms together provide complete robustness.

---

## Scope

**Files/modules touched:**
- `etsy mockup creator/src/generator.py` — Add `theme_name` optional param and add `no_bg` variants to parent folder fallback tuple.
- `etsy mockup creator/src/main.py` — Add `--theme-name` CLI argument in `argparse` and pass to `Generator.generate_all`.
- `etsy mockup creator/web_editor/server.py` — Add `no_bg` variants to parent folder fallback tuple for web editor consistency.
- `etsy_pipeline/workers/mockup_worker.py` — Pass `--theme-name` when invoking `etsy mockup creator` subprocess.

**Out of scope:**
- Modifying `hero.json` layout or font styling.

---

## Risks & edge cases
- Theme folder names with trailing numbers (e.g. `dino_clipart_01`) — `re.sub(r'[\s_\-]*\d+$', '', ...)` strips trailing numbers correctly.
- Missing `job.theme` — Fall back to `job.theme_slug.replace("_", " ")`.

---

## Steps
1. Update `etsy mockup creator/src/generator.py`: add `theme_name` param and expand subfolder tuple.
2. Update `etsy mockup creator/src/main.py`: add `--theme-name` CLI arg.
3. Update `etsy mockup creator/web_editor/server.py`: expand subfolder tuple.
4. Update `etsy_pipeline/workers/mockup_worker.py`: pass `--theme-name` in subprocess command.
5. Run linting (`ruff check . --fix`) and type check (`mypy etsy_pipeline`).
6. Run tests to ensure no regressions.

---

## Rollback
Git revert changes to `mockup_worker.py` and `etsy mockup creator` files.
