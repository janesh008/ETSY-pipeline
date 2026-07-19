# High-Level Responsibilities — `pipeline`

This subpackage is the pipeline orchestrator, responsible for sequencing the workers and coordinating the execution flow.

## What it is responsible for
*   Instantiating workers and calling them in sequential order.
*   Updating `Job` state statuses and catching stage exceptions safely.
*   Exposing a single entry function (`Pipeline.run`) for execution.

## What it is NOT responsible for
*   Any actual business logic (no API client calls, prompt formatting, image rendering, or file parsing).
