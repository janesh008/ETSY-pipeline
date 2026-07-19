# CONTEXT.md — `scripts/`

**Last reviewed:** 2026-07-19

## Responsibility
CLI entry points and developer tooling scripts. These are runnable directly (`python scripts/foo.py`) or via `python -m scripts.foo`. Not part of the installable package.

## Not responsible for
Business logic — scripts are thin wrappers that parse CLI args, instantiate `Pipeline`, and pretty-print results. All real work happens in `etsy_pipeline/`.

## Public interface (scripts)

| Script | Purpose | Usage |
|--------|---------|-------|
| `run_prompts.py` | Run prompt generation and save output | `python -m scripts.run_prompts --theme "X" --event birthday` |
| `build_graph.py` | Regenerate `.repo-graph/graph.json` | `python scripts/build_graph.py [--check]` |

## Dependencies
- `etsy_pipeline.*` (all subpackages — scripts are the top of the import stack)
- `argparse` (stdlib)
- `pathlib`, `sys` (stdlib)

## Gotchas / invariants
- Scripts add `REPO_ROOT` to `sys.path` at the top so they work both as `python scripts/foo.py` and `python -m scripts.foo`. Do not remove this.
- `build_graph.py --check` is used by the pre-commit hook and CI. It exits 0 if graph is current, 1 if stale. Keep this behavior — changing the exit code will silently break CI.
- `run_prompts.py` saves both `prompts_raw.txt` (Gemini response verbatim) and a parsed `<theme>.txt`.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:** (no subdirectories)
- **Key files:** [`run_prompts.py`](run_prompts.py), [`build_graph.py`](build_graph.py)
