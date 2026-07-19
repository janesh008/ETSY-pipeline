# Coding Skills & Rules — `models`

When modifying data models:

## 1. Job Object is Mutable
Workers receive a `Job` instance, modify its properties directly (e.g., adding logs or completed states), and return it. Do not attempt to deep-copy or clone jobs inside workers.

## 2. Default Values & Factories
*   Always use `Field(default_factory=...)` for mutable types (like lists, dicts, datetimes) so they are initialized fresh for each new `Job` instance.
*   Avoid standard mutable defaults (like `default=[]` or `default={}`).

## 3. Fixed Stages Dict
*   The `Job.stages` keys are hardcoded to represent the 8 sequential stages. If a new stage is introduced, it must be added to the Pydantic default list initialization in `job.py`.
