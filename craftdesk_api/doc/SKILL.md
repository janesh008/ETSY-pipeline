# CraftDesk API Backend — Coding Rules, Gotchas & Development Standards

## 📜 Development Rules & Layering Guidelines

Imports in `craftdesk_api` must strictly follow an upward dependency flow:

```
core / db / models  ←  schemas  ←  services  ←  routers  ←  main.py / tests
```

- **`core/` & `models/`** must never import from `routers/` or `services/`.
- Every router must use **Pydantic schemas** (`schemas/`) for input validation and response serialization.
- Every endpoint returning HTTP 204 No Content **must set `response_model=None`** in the decorator to avoid FastAPI assertion errors.

---

## ⚠️ GOTCHAS & Critical Pitfalls

### 1. HTTP 204 No Content Assertion
- **Problem:** FastAPI raises `AssertionError: Status code 204 must not have a response body` if `response_model` is specified or inferred.
- **Rule:** Always write `@router.delete(..., status_code=204, response_model=None)`.

### 2. SQLite vs PostgreSQL SQLAlchemy Engine Arguments
- **Problem:** PostgreSQL pool arguments (`pool_size`, `max_overflow`) crash when passed to SQLite in test environments.
- **Rule:** Conditionally omit pool arguments if `DATABASE_URL` starts with `sqlite`.

### 3. Fernet Key Requirements
- **Problem:** Cryptography Fernet keys must be exactly 32 URL-safe base64-encoded bytes.
- **Rule:** Always generate keys using `Fernet.generate_key().decode()`. Never hardcode plain strings.

### 4. Async Test Fixture Scoping
- **Problem:** `TestClient` makes synchronous requests, but FastAPI route handlers execute async SQLAlchemy queries.
- **Rule:** Use `create_async_engine("sqlite+aiosqlite:///:memory:")` inside `conftest.py` with `asyncio.run()` during table creation and teardown.

---

## 🧪 Testing Standards (`pytest`)

- Execute tests with:
  ```bash
  python -m pytest craftdesk_api/tests/ -v --rootdir=craftdesk_api
  ```
- All test fixtures live in `craftdesk_api/tests/conftest.py`.
- Mock external APIs (GCP Compute API, Etsy OAuth token endpoints, Gemini 2.5 API) using `unittest.mock.patch` to keep test suites deterministic, offline-capable, and fast.
