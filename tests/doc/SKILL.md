# Coding Skills & Rules — `tests`

When writing new tests:

## 1. Fast Unit Tests
*   Never write unit tests that make real network connections.
*   Instead, mock API clients or use static mock data (like `sample_gemini_response`) to verify parsers and validators.

## 2. API Key Protection
*   Integration tests must be marked with `@pytest.mark.integration`.
*   These are skipped in default test runs (`pytest tests/ -k "not integration"`) to protect developers from using API credits by accident.

## 3. Cache Clears
Tests modifying configuration settings at runtime must call `get_settings.cache_clear()` inside setup/teardown methods so changes don't leak into subsequent test runs.
