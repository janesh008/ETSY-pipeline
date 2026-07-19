# Coding Skills & Rules — `utils`

When editing exceptions or logging helpers:

## 1. Exceptions Invariant
*   All custom exceptions must inherit from the base `PipelineError` class.
*   Worker-specific errors must inherit from the corresponding stage error (e.g. `PromptValidationError` inherits from `PromptGenerationError`).
*   Always include the target `stage` and `job_id` strings (where available) so error logs are fully searchable in GCP Stackdriver.

## 2. No Print Statements
*   Never write `print()` in pipeline code. Use `get_logger(__name__)` to fetch the formatted logger instance.
*   Print statements bypass standard out formatting and will fail to parse properly in cloud logging environments.
