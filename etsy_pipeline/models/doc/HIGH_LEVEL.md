# High-Level Responsibilities — `models`

This subpackage defines the unified data structures that hold state for a pipeline run.

## What it is responsible for
*   Governing the structure of the `Job` object, which holds inputs, state, and outputs for all 8 stages.
*   Enforcing validation rules on job parameters using Pydantic.

## What it is NOT responsible for
*   Saving or loading jobs to files, storage buckets, or databases (persistence).
*   Executing worker operations or scheduling stages.
