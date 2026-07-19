# Package-Level Coding Skills & Rules — `etsy_pipeline/`

When editing any code inside this package, you must follow these standards:

## 1. Upward Layering Rule
Imports must only flow upward: `config` ← `models` ← `utils` ← `workers` ← `pipeline`.
*   A lower module (like `models/`) must never import from a higher module (like `workers/`).
*   Check the graph edges in `.repo-graph/graph.json` after adding imports to ensure you haven't introduced a circular dependency.

## 2. Docstrings & Type Hints
*   Every public function, method, and class must have a Google-style docstring.
*   Every public function must have full Python type hints.
*   The first line of the docstring must match the docstring summary field in the code graph.

## 3. Logging & Exception Invariant
*   Never use `print()` in package code. Use `get_logger(__name__)` from `etsy_pipeline.utils.logging`.
*   All worker failures must raise a subclass of `PipelineError` defined in `etsy_pipeline.utils.exceptions`.
