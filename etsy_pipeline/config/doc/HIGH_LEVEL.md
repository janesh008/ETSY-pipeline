# High-Level Responsibilities — `config`

This subpackage is responsible for loading, parsing, and validating runtime configuration settings from environment variables and local `.env` files.

## What it is responsible for
*   Providing a cached, single source of truth for all pipeline settings via the `Settings` class.
*   Resolving package paths and directories.

## What it is NOT responsible for
*   Verifying that credentials are active or that external systems (like Vertex AI or ComfyUI) are reachable.
