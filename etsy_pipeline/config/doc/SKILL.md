# Coding Skills & Rules — `config`

When editing settings or adding configuration keys:

## 1. No Magic Strings
All hardcoded values must live in `settings.py`. Never hardcode API keys, path suffixes, or default variables inside workers.

## 2. Environment Variables
*   Every new setting field must be added to the `Settings` Pydantic class with an appropriate type hint.
*   Document the new field in `.env.example`.
*   Fields must be documented with a `Field(description=...)` declaration.

## 3. Cache Management Gotcha
`get_settings()` is wrapped in `@lru_cache(maxsize=1)`. If you programmatically update settings or patch env vars in tests, you must call `get_settings.cache_clear()` to force settings to reload.
