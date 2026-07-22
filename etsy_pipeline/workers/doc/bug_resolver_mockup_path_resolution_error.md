# Bug Fix Walkthrough — Fix Path Resolution in Mockup Worker Subprocess

We resolved the path resolution failure in the mockup worker's subprocess execution.

## Changes Made

### 1. Absolute Path Resolution
- Modified [mockup_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/mockup_worker.py) to resolve `input_dir`, `output_dir`, and the `templates` path to absolute paths via `.resolve()` before passing them as command-line arguments.
- This ensures that even if `cwd` is switched to the `etsy mockup creator` subdirectory, relative directories like `output/` resolve correctly based on the workspace root instead of yielding `Theme directory does not exist` errors.

## Verification & Testing

- Verified that mockup generator succeeds when relative paths are specified in config settings.
- The subprocess successfully executes, reads transparent clipart images, and saves mockup files to the correct output folder.
