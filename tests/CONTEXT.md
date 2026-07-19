# CONTEXT.md — `tests/`

**Last reviewed:** 2026-07-19

## Responsibility
Automated tests for the `etsy_pipeline` package. Unit tests run without external API access; integration tests (marked `@pytest.mark.integration`) call real APIs and are excluded from the default run.

## Not responsible for
Testing the legacy Colab notebooks in `ETSY_main_colab/` or the `etsy mockup creator/` sub-project.

## Public interface (test commands)
```bash
# Unit tests only (fast, no API keys needed)
pytest tests/ -v -k "not integration"

# Integration tests (requires .env with valid credentials)
pytest tests/ -v -k "integration"

# All tests
pytest tests/ -v
```

## Dependencies
- `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`
- `etsy_pipeline.*` — the package under test
- No test doubles (mocks) for unit tests — instead, sample fixture data mimics the real Gemini response format exactly

## Gotchas / invariants
- **The `sample_gemini_response` fixture in `test_prompt_worker.py` is the ground truth for the parser.** If SKILL.md changes its output format (section headings, numbering, inactive section marker), update this fixture first, then fix the parser.
- **Integration tests use real API credits.** Run them deliberately; never add them to a fast-feedback loop (e.g. file-watcher auto-test).
- When adding a new worker, add a corresponding `tests/test_<worker>_worker.py` with at minimum: a parse/output test using a fixture, a validation-failure test, and one `@pytest.mark.integration` end-to-end test.
- `get_settings.cache_clear()` must be called in any test that patches environment variables — otherwise the cached settings from a previous test will bleed through.

## Navigation
- **↑ Parent:** [`../CONTEXT.md`](../CONTEXT.md)
- **↓ Children:** (no subdirectories)
- **Key file:** [`test_prompt_worker.py`](test_prompt_worker.py)
