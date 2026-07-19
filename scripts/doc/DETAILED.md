# Code Details — `scripts`

## Code Behavior
This folder contains:
*   [📄 run_prompts.py](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts/run_prompts.py) — CLI entry point.
*   [📄 build_graph.py](file:///d:/Janesh/ETSY/ETSY-pipeline/scripts/build_graph.py) — Code graph generator.

### `run_prompts.py`
1.  **Arguments:** Accepts `--theme` (required), `--event` (default `"Normal"`), `--style` (optional), and `--count` (optional).
2.  **Job Creation:** Instantiates a new Pydantic `Job` with the CLI parameters.
3.  **Pipeline Invocation:** Runs `setup_logging()`, instantiates `Pipeline()`, and calls `pipeline.run(job)`.
4.  **Save Output:** Exposes `save_prompts_to_files(job)` which parses the completed job prompts and writes them to:
    *   `output/<theme>_prompts_raw.txt`: The raw text response from Gemini.
    *   `output/<theme>.txt`: A structured text file grouped by locked headings (compatible with legacy loaders).

### `build_graph.py`
1.  **Parsing:** Walks `etsy_pipeline/`, `scripts/`, and `tests/` using Python's stdlib `ast` parser.
2.  **Extraction:** Extracts module definitions, class declarations, method descriptions, parameter signatures, and import/call edges.
3.  **Determinism:** Sorts all nodes and edges alphabetically to ensure identical files produce identical graph outputs.
4.  **Checks:** In `--check` mode, hashes the newly built graph against the existing `.repo-graph/graph.json` to verify it is up to date, exiting with a non-zero status code if stale.
