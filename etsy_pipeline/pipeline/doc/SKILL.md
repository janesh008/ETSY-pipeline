# Coding Skills & Rules — `pipeline`

When editing the orchestrator:

## 1. Keep it Stateless
*   The `Pipeline` class instantiates workers once during initialization.
*   Make sure no job-specific state is cached on `Pipeline` or its workers. If state is stored on `self` inside a worker, it will leak to subsequent runs.

## 2. Sequential Logic
*   The stage ordering is explicitly declared in `Pipeline.run()`.
*   Ensure that any new worker stage is added to the sequencing array and mapped in `run_stage()` for single-stage debug support.

## 3. Handle Exceptions Gracefully
*   Always catch custom exceptions (`PipelineError`) raised by workers.
*   Record the failure in `Job.stages` and `Job.add_error` so the orchestrator halts safely without crashing the parent process.
