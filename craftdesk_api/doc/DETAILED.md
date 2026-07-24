# CraftDesk API Backend — Detailed Technical Specification & Module Reference

## 📁 File Structure Map

```
craftdesk_api/
├── core/
│   ├── config.py           # Pydantic Settings (DATABASE_URL, JWT_SECRET, FERNET_KEY)
│   └── security.py         # Fernet AES-256 encrypt/decrypt, bcrypt, JWT encode/decode
├── db/
│   └── base.py             # Async SQLAlchemy engine (Neon.tech), SessionLocal, get_db
├── models/
│   ├── user.py             # User ORM model (users table)
│   ├── etsy_shop.py        # EtsyShop ORM model (etsy_shops table)
│   ├── gcp_config.py       # GcpConfig ORM model (gcp_configs table)
│   └── api_key.py          # ApiKey ORM model (api_keys table)
├── schemas/
│   ├── auth.py             # Auth Pydantic schemas
│   ├── gcp.py              # GCP Pydantic schemas
│   ├── prompts.py          # Prompt Studio Pydantic schemas
│   ├── etsy.py             # Etsy OAuth & Shop Pydantic schemas
│   ├── pipeline.py         # Pipeline Runner Pydantic schemas
│   ├── review.py           # Review & Publishing Pydantic schemas
│   └── settings.py         # Settings & API Keys Pydantic schemas
├── services/
│   ├── gcp_vm.py           # GCP Compute Engine API v1 & ComfyUI health check poller
│   ├── etsy_scraper.py     # Etsy listing URL web scraper (httpx + BeautifulSoup)
│   ├── prompt_engine.py    # Gemini 2.5 Flash prompt synthesis engine
│   ├── etsy_oauth.py       # Etsy OAuth 2.0 PKCE helper (verifier, challenge, tokens)
│   ├── pipeline_runner.py  # 6-stage pipeline execution state machine & retry logic
│   └── etsy_publisher.py   # Etsy Open API v3 draft listing publisher
├── routers/
│   ├── auth.py             # /register, /login, /refresh, /logout endpoints
│   ├── gcp.py              # /gcp/config, /gcp/vm/start, /gcp/vm/stop, /gcp/vm/status
│   ├── prompts.py          # /prompts/scrape-etsy, /prompts/generate, /jobs/{id}/export
│   ├── etsy.py             # /etsy/auth/url, /etsy/auth/callback, /etsy/shops
│   ├── pipeline.py         # /pipeline/jobs, /jobs/{id}/stages/{stage}/retry, WS stream
│   ├── review.py           # /review/{id}, /review/{id}/metadata, /review/{id}/push-to-etsy
│   └── settings.py         # /settings/profile, /settings/api-keys
├── tests/
│   ├── conftest.py         # Shared aiosqlite test database fixture & env var overrides
│   ├── test_auth.py        # 16 security & auth unit tests
│   ├── test_gcp.py         # 7 GCP router unit tests
│   ├── test_prompts.py     # 4 Prompt Studio unit tests
│   ├── test_etsy.py        # 3 Etsy OAuth unit tests
│   ├── test_pipeline.py    # 3 Pipeline runner unit tests
│   ├── test_review.py      # 3 Review & Etsy publishing unit tests
│   └── test_settings.py    # 3 Settings unit tests
└── main.py                 # FastAPI entry point, CORS configuration, router mounts
```

---

## 🔍 Module Deep-Dive

### 1. `core/security.py`
- `encrypt(plaintext: str) -> str`: Encrypts string using `cryptography.fernet.Fernet` with `FERNET_KEY`.
- `decrypt(ciphertext: str) -> str`: Decrypts Fernet token back to plaintext string.
- `hash_password(password: str) -> str`: Hashes password using bcrypt.
- `verify_password(plain: str, hashed: str) -> bool`: Verifies password match.
- `create_access_token(user_id: str) -> str`: Issues 60-minute JWT with `{"sub": user_id, "type": "access"}`.
- `create_refresh_token(user_id: str) -> str`: Issues 30-day JWT with `{"sub": user_id, "type": "refresh"}`.

### 2. `services/gcp_vm.py`
- `start_vm()`: Builds `googleapiclient.discovery` compute v1 client and executes `instances().start()`.
- `stop_vm()`: Executes `instances().stop()`.
- `get_vm_details()`: Executes `instances().get()`, returning status (`RUNNING`/`STOPPED`) and external IP (`natIP`).
- `check_comfy_ui_health(host: str, port: int)`: Sends `GET http://<host>:<port>/` via `httpx.AsyncClient(timeout=3.0)` to verify ComfyUI readiness.

### 3. `services/prompt_engine.py`
- `generate_prompts()`: Combines Theme Text, Etsy Scraped Context, and Reference Images. Invokes `google.genai` model `gemini-2.5-flash` with system prompt. Formats output into sectioned numbered prompts and a clean exportable `.txt` file string.

### 4. `services/etsy_oauth.py`
- `generate_pkce_pair()`: Generates 64-char `code_verifier` and SHA256 base64url `code_challenge`.
- `get_auth_url()`: Builds Etsy OAuth consent URL with `listings_r listings_w shops_r` scopes.
- `exchange_code_for_tokens()`: POSTs `code` + `code_verifier` to `https://api.etsy.com/v3/public/oauth/token`.

### 5. `services/pipeline_runner.py`
- Manages stage status transitions: `pending` → `running` → `completed` or `failed`.
- On stage failure, records `error_message` (root exception) and `stderr_log` (traceback).
- Provides `retry_stage(job_id, stage_name)` to reset and re-run only the target failed stage.

### 6. `services/etsy_publisher.py`
- Decrypts shop access token from `etsy_shops` table via Fernet.
- Sends POST to `https://openapi.etsy.com/v3/application/shops/{shop_id}/listings` with `taxonomy_id=10985` (digital craft clipart), truncated title (max 140), and tags (max 13 items, 20 chars each).
