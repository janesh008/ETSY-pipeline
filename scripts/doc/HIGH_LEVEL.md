# High-Level Responsibilities — `scripts`

This folder contains runnable CLI commands and developer setup tools. These files are not packaged as part of the core Python library.

## What it is responsible for
*   Providing command-line tools to trigger pipeline runs (`run_prompts.py`).
*   Providing code graph generators to update the repository map (`build_graph.py`).

## What it is NOT responsible for
*   Any pipeline logic or data modeling.
