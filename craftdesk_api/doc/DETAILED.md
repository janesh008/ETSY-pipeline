# CraftDesk API Backend — Module-by-Module Business Logic Specification

This document provides an exhaustive breakdown of every module in `craftdesk_api`, detailing its **Business Goal**, **Domain Input & Output Contracts**, **Step-by-Step Business Logic Algorithm**, and **Failure Recovery Strategies**.

---

## 📁 1. Core & Database Layer

### `craftdesk_api/core/config.py`
- **Business Goal:** Centralizes all environment configuration to prevent hardcoded credentials across the codebase.
- **Business Input:** Environment variables or local `.env` file (`DATABASE_URL`, `JWT_SECRET_KEY`, `FERNET_KEY`).
- **Domain Algorithm:** Uses `pydantic-settings` to load and validate variables. Provides fallback development defaults (`sqlite+aiosqlite:///craftdesk.db`) so local execution never crashes if a non-critical variable is omitted.

### `craftdesk_api/core/security.py`
- **Business Goal:** Protects seller credentials and session integrity using enterprise-grade cryptography.
- **Domain Contracts:**
  - `encrypt(plaintext: str) -> str`: Converts sensitive API keys or OAuth tokens into AES-256 Fernet ciphertext.
  - `decrypt(ciphertext: str) -> str`: Restores original credentials for active API calls.
  - `hash_password(password: str) -> str`: Hashes passwords via `bcrypt` (cost factor 12).
  - `create_access_token(user_id: str) -> str`: Issues 60-minute JWT with claims `{"sub": user_id, "type": "access"}`.
  - `create_refresh_token(user_id: str) -> str`: Issues 30-day JWT with claims `{"sub": user_id, "type": "refresh"}`.
- **Risk Mitigation:** If ciphertext is tampered with, `decrypt()` raises an exception rather than returning corrupted keys.

### `craftdesk_api/db/base.py` & `models/`
- **Business Goal:** Manages relational SaaS entity persistence in Neon.tech PostgreSQL.
- **Entity Schemas:**
  - `User` (`users` table): `id`, `email`, `password_hash`, `full_name`, `created_at`.
  - `EtsyShop` (`etsy_shops` table): `id`, `user_id`, `shop_id`, `shop_name`, `encrypted_access_token`, `encrypted_refresh_token`, `token_expires_at`, `is_active`.
  - `GcpConfig` (`gcp_configs` table): `id`, `user_id`, `project_id`, `zone`, `instance_name`, `encrypted_service_account_json`, `comfy_ui_port`.
  - `ApiKey` (`api_keys` table): `id`, `user_id`, `service`, `encrypted_api_key`.

---

## 📁 2. Business Services Layer (`craftdesk_api/services/`)

### `services/gcp_vm.py` — GPU Cloud Cost Minimizer
- **Business Goal:** Controls GCP Compute Engine GPU instance lifecycles to ensure sellers only pay for active rendering minutes.
- **Business Logic Algorithm:**
  1. `start_vm()`: Parses decrypted GCP service account JSON, constructs `googleapiclient.discovery` Compute Engine v1 client, and triggers `instances().start()`.
  2. `stop_vm()`: Triggers `instances().stop()`, shutting down the GPU VM to stop billing.
  3. `get_vm_details()`: Polls `instances().get()` to extract status (`RUNNING`/`STOPPED`) and external NAT IP.
  4. `check_comfy_ui_health(host, port)`: Asynchronously issues `GET http://<host>:<port>/` via `httpx.AsyncClient(timeout=3.0)`. Returns `True` only when ComfyUI web server responds HTTP 200.

### `services/etsy_scraper.py` — Competitor Market Intelligence Scraper
- **Business Goal:** Extracts design trends, keywords, and gallery image layouts from top-selling Etsy product listings.
- **Business Logic Algorithm:**
  1. Validates input URL against Etsy listing regex (`etsy.com/listing/\d+`).
  2. Sends HTTP GET request with Chrome User-Agent header to avoid bot detection blocks.
  3. Parses HTML using BeautifulSoup:
     - Title: Extracts `og:title` meta tag or `<h1>` header text.
     - Description: Extracts `og:description` or meta description.
     - Images: Extracts `og:image` and up to 5 gallery thumbnails matching `il_\d+xN` URL pattern.
- **Failure Mitigation:** If scraping encounters HTTP errors, returns a clean structured fallback object so prompt generation can still proceed.

### `services/prompt_engine.py` — Multi-Input AI Prompt Synthesis
- **Business Goal:** Generates 22–100 commercial watercolor clipart prompts tailored for Midjourney or ComfyUI.
- **Business Logic Algorithm:**
  1. Synthesizes context from Text Theme, Etsy Scraped Title/Description, and Reference Images.
  2. Constructs prompt instructions requiring output of numbered prompts detailing subject, pose, color palette, pastel watercolor splatters, and transparent background isolation.
  3. Invokes Gemini 2.5 Flash API (`gemini-2.5-flash`).
  4. Parses raw response, stripping numbers (`1. `, `01. `) and cleaning whitespace.
  5. Formats output into a downloadable `.txt` file string with header comments and numbered entries.

### `services/etsy_oauth.py` — PKCE OAuth 2.0 Store Security Helper
- **Business Goal:** Enables sellers to connect Etsy shops without sharing passwords or client secrets.
- **Business Logic Algorithm:**
  1. `generate_pkce_pair()`: Generates 64-char random `code_verifier` and SHA256 base64url digest `code_challenge`.
  2. `get_auth_url()`: Builds Etsy OAuth consent URL with `listings_r listings_w shops_r` scopes and PKCE parameters (`code_challenge_method=S256`).
  3. `exchange_code_for_tokens()`: POSTs `code` + `code_verifier` to `https://api.etsy.com/v3/public/oauth/token`.
  4. `get_shop_details()`: Calls `https://openapi.etsy.com/v3/application/users/me` and `/shops` to retrieve shop ID and shop name.

### `services/pipeline_runner.py` — 6-Stage Real Assembly Line & Retry Engine
- **Business Goal:** Manages real 6-stage pipeline execution using `etsy_pipeline` worker modules, GCS prompt file injection, live item progress, ETA calculations, date folder retention, module-level checkpoint recovery, and stop/cancellation controls. (See detailed guide in [`doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)).
- **Business Logic Algorithm:**
  1. `create_job()`: Loads and parses the selected GCS prompt file (`gs://.../Clipart/<date>/<slug>/<slug>.txt`) or local file into `Job.prompts` using `PromptWorker._parse_response`. Preserves `date_folder` from prompt file path (e.g. `Clipart/2026-07-22/`).
  2. Initializes 6 stages (`image_gen`, `bg_removal`, `upscaling`, `mockup_creation`, `pdf_generation`, `metadata_generation`) in `pending` state.
  3. `_is_stage_100pct_complete()`: Checks GCS bucket prefix `Clipart/<date>/<theme>/<stage>/` and local `output/Clipart/<date>/<theme>/<stage>/`. If 100% of expected PNG files exist, marks stage `Completed ✅` immediately and skips worker execution.
  4. `stop_job(job_id)`: Cancels active `asyncio.Task`, sets job and running stage status to `failed` (`"Pipeline execution stopped by user."`).
  5. `run_full_pipeline_async()`: Sequentially executes `etsy_pipeline` worker modules (`ImageWorker`, `BackgroundRemovalWorker`, `UpscaleWorker`, `MockupWorker`, `MetadataWorker`) in background threads (`asyncio.create_task(asyncio.to_thread(...))`).
  6. Tracks live item counters (`images_done`/`images_total`), elapsed seconds, and estimated time remaining (ETA) per stage. Safely accesses `st_res.error_message` on `StageResult` models to prevent `AttributeError` crashes in the stage monitoring loop.
  7. For `mockup_creation`, dynamically counts generated mockup PNG files in the local `mockups` workspace directory to scale progress smoothly between 10% and 90% during subprocess execution.
  8. If a stage throws an exception:
     - Sets stage status to `failed`.
     - Captures root exception message (`error_message`) and full traceback (`stderr_log`).
     - Halts execution while preserving completed assets from earlier stages.
  9. `run_stage_execution(job_id, stage_name)`: Resets target stage status to `pending`, clears error log, and re-executes only that specific stage.

### `services/etsy_publisher.py` — Etsy API v3 Draft Listing Publisher
- **Business Goal:** Automatically creates draft digital clipart listings on Etsy.
- **Business Logic Algorithm:**
  1. Truncates listing title to max 140 chars (Etsy API limit).
  2. Cleans and truncates tags to max 13 items, max 20 chars per tag.
  3. POSTs payload to `https://openapi.etsy.com/v3/application/shops/{shop_id}/listings` with:
     - `taxonomy_id`: `10985` (Digital Craft / Clipart)
     - `is_digital`: `true`
     - `type`: `download`
     - `state`: `draft`
  4. Returns `listing_id` and Etsy seller dashboard URL (`https://www.etsy.com/your/shops/me/listings/{id}`).

---

## 📁 3. FastAPI Routers Layer (`craftdesk_api/routers/`)

### `routers/auth.py`
- `POST /api/v1/auth/register`: Validates user registration payload, hashes password, creates user record in DB.
- `POST /api/v1/auth/login`: Authenticates email & password, returns Access & Refresh JWTs.
- `POST /api/v1/auth/refresh`: Issues new Access Token from valid Refresh Token.
- `POST /api/v1/auth/logout`: Clears session (HTTP 204 No Content with `response_model=None`).

### `routers/gcp.py`
- `POST /api/v1/gcp/config`: Encrypts service account JSON key via Fernet AES-256 and saves GCP VM details.
- `GET /api/v1/gcp/config`: Returns GCP config metadata (hides key).
- `POST /api/v1/gcp/vm/start`: Triggers GPU VM start signal.
- `POST /api/v1/gcp/vm/stop`: Triggers GPU VM stop signal to save costs.
- `GET /api/v1/gcp/vm/status`: Returns VM status (`RUNNING`/`STOPPED`) and polls ComfyUI `:8188` health.

### `routers/prompts.py`
- `POST /api/v1/prompts/scrape-etsy`: Scrapes competitor Etsy URL for title, description, and images.
- `POST /api/v1/prompts/generate`: Synthesizes prompt matrix using Gemini 2.5.
- `GET /api/v1/prompts/jobs/{job_id}/export`: Streams plain text (`.txt`) file attachment for download.

### `routers/etsy.py`
- `GET /api/v1/etsy/auth/url`: Generates PKCE authorization URL & verifier.
- `POST /api/v1/etsy/auth/callback`: Exchanges authorization code for tokens, encrypts tokens via AES-256 Fernet, and saves connected shop.
- `GET /api/v1/etsy/shops`: Lists user's connected Etsy stores.
- `DELETE /api/v1/etsy/shops/{shop_db_id}`: Deactivates shop connection.

### `routers/prompts.py`
- `GET /api/v1/prompts`: Scans GCS bucket (`gs://<bucket>/Clipart/`) **first** and local disk second. Returns list of available prompt files with `gcs_path`, `is_gcs`, `preview`, and prompt counts.

### `routers/pipeline.py`
- `POST /api/v1/pipeline/jobs`: Starts 6-stage pipeline job in background. Resolves prompt text from GCS bucket first (`gs://...`), preventing missing local file errors.
- `GET /api/v1/pipeline/jobs/{job_id}`: Returns job status and stage progress array.
- `POST /api/v1/pipeline/jobs/{job_id}/stages/{stage_name}/retry`: Re-runs single failed stage.
- `WS /api/v1/pipeline/jobs/{job_id}/stream`: WebSocket streaming real-time stage updates.

### `routers/review.py`
- `GET /api/v1/review/{job_id}`: Returns Hero image, all 4 mockups, PDF download link, and metadata.
- `PUT /api/v1/review/{job_id}/metadata`: Saves inline edits to title, description, or 13 tags.
- `POST /api/v1/review/{job_id}/push-to-etsy`: Publishes draft listing to selected connected Etsy shop.

### `routers/settings.py`
- `PUT /api/v1/settings/profile`: Updates user profile name.
- `POST /api/v1/settings/api-keys`: Encrypts and saves Gemini/Replicate API keys.
- `GET /api/v1/settings/api-keys`: Lists saved API key services.
- `DELETE /api/v1/settings/api-keys/{service}`: Removes saved API key.
