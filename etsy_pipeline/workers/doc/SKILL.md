# Coding Skills & Rules — `workers`

When writing or modifying pipeline workers:

## 1. Zero Job State
Workers must not store job-specific parameters on `self`. They should act as stateless functions. Caching connections or API client instances is permitted, but caching job parameters is forbidden.

## 2. Pydantic-Worker Contract
*   The worker's entry point is always `run(job: Job) -> Job`.
*   Workers should call `job.add_log()` to write logs and use Pydantic models for structured output parameters.

## 3. Strict Parser Validation
*   Workers parsing LLM outputs must perform schema validation.
*   For example, `PromptWorker` verifies that active sections contain at least 10 prompts and that all locked section headings exist. Failures must raise clear, actionable exceptions (`PromptValidationError`).
