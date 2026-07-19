# Code Details — `pipeline`

## Code Behavior
This subpackage contains:
*   [📄 orchestrator.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/pipeline/orchestrator.py)

Contains the core orchestration class:

### Class: `Pipeline`
*   `__init__()`: Loads settings via `get_settings()` and instantiates all stage workers (currently only `PromptWorker` is mapped).
*   `run(job)`:
    1.  Sets `job.status = JobStatus.RUNNING`.
    2.  Loops through the sequence of stage names (e.g. `"prompt_generation"`).
    3.  Calls `run_stage()` for each stage.
    4.  If a stage fails, catches the exception, logs it, and immediately exits the loop, setting `job.status = JobStatus.FAILED`.
    5.  If all stages succeed, sets `job.status = JobStatus.COMPLETED`.
*   `run_stage(job, stage_name)`:
    1.  Resolves the stage worker from its internal `worker_map`.
    2.  Transitions the stage result state to running.
    3.  Calls the worker's `run(job)` method.
    4.  Logs the duration and sets status to completed.
    5.  Catches `PipelineError`, records error details inside the stage result, and re-raises so the master execution loop halts.
