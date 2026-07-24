# CraftDesk Phase 1 — Task Tracker

## Step 1: FastAPI Backend Foundation ✅
- [x] Create `craftdesk_api/` directory structure
- [x] `pyproject.toml` — add `craftdesk_api` dependencies
- [x] `craftdesk_api/core/config.py` — Settings (Neon.tech DSN, JWT secret, Fernet key)
- [x] `craftdesk_api/core/security.py` — AES-256 Fernet encrypt/decrypt + bcrypt + JWT
- [x] `craftdesk_api/db/base.py` — SQLAlchemy engine + session factory (Neon.tech)
- [x] `craftdesk_api/models/user.py` — `users` table ORM model
- [x] `craftdesk_api/models/etsy_shop.py` — `etsy_shops` table ORM model
- [x] `craftdesk_api/models/gcp_config.py` — `gcp_configs` table ORM model
- [x] `craftdesk_api/models/api_key.py` — `api_keys` table ORM model
- [x] `craftdesk_api/alembic/` — Alembic migrations setup + initial migration
- [x] `craftdesk_api/schemas/auth.py` — Pydantic request/response schemas
- [x] `craftdesk_api/routers/auth.py` — /register /login /refresh /logout endpoints
- [x] `craftdesk_api/main.py` — FastAPI app entry point with CORS + router wiring
- [x] `craftdesk_api/tests/test_auth.py` — 16/16 pytest tests passing
- [x] `.env.example` — CraftDesk env vars added
- [ ] `pyproject.toml` — add `craftdesk_api` dependencies
- [ ] `craftdesk_api/core/config.py` — Settings (Neon.tech DSN, JWT secret, Fernet key)
- [ ] `craftdesk_api/core/security.py` — AES-256 Fernet encrypt/decrypt + bcrypt + JWT
- [ ] `craftdesk_api/db/base.py` — SQLAlchemy engine + session factory (Neon.tech)
- [ ] `craftdesk_api/models/user.py` — `users` table ORM model
- [ ] `craftdesk_api/models/etsy_shop.py` — `etsy_shops` table ORM model
- [ ] `craftdesk_api/models/gcp_config.py` — `gcp_configs` table ORM model
- [ ] `craftdesk_api/models/api_key.py` — `api_keys` table ORM model
- [ ] `craftdesk_api/alembic/` — Alembic migrations setup + initial migration
- [ ] `craftdesk_api/schemas/auth.py` — Pydantic request/response schemas
- [ ] `craftdesk_api/routers/auth.py` — /register /login /refresh /logout endpoints
- [ ] `craftdesk_api/main.py` — FastAPI app entry point with CORS + router wiring
- [ ] `craftdesk_api/tests/test_auth.py` — pytest tests for all auth endpoints
- [ ] `.env.example` — add CraftDesk env vars (DATABASE_URL, JWT_SECRET, FERNET_KEY)

## Step 2: Next.js Frontend + Design System + Auth Pages ✅
- [x] Scaffold `craftdesk_web/` (Next.js 14 App Router + TypeScript + Tailwind)
- [x] Design tokens CSS (`globals.css` Editorial Atelier `#F7F6F0` palette + Outfit/Inter/JetBrains Mono fonts)
- [x] `src/lib/api.ts` — TypeScript API client for FastAPI endpoints
- [x] `src/context/AuthContext.tsx` — Auth state management & token persistence
- [x] `/login` page — Editorial Atelier login UI
- [x] `/register` page — Editorial Atelier register UI
- [x] Protected route & auth redirect logic

## Step 3: Dashboard ✅
- [x] `/dashboard` page
- [x] Stats cards (prompts, pipelines, shops)
- [x] GPU VM status widget (stopped, booting, ready with Start/Stop action)
- [x] Quick action navigation cards (Prompt Studio, Pipeline, Etsy Shops)


## Step 4: GCP VM Manager ✅
- [x] `craftdesk_api/schemas/gcp.py` — Pydantic request/response schemas
- [x] `craftdesk_api/services/gcp_vm.py` — GCP Compute Engine API wrapper & ComfyUI health check poller
- [x] `craftdesk_api/routers/gcp.py` — /config (save/get), /vm/start, /vm/stop, /vm/status endpoints
- [x] `craftdesk_api/tests/test_gcp.py` — 7 pytest tests passing (23/23 total backend tests green)
- [x] Integrated GCP status widget on frontend dashboard


## Step 5: Multi-Input Prompt Studio ✅
- [x] `craftdesk_api/services/etsy_scraper.py` — Etsy product listing URL web scraper (title, description, thumbnails)
- [x] `craftdesk_api/services/prompt_engine.py` — Multi-input prompt generation engine (Gemini 2.5 + offline fallback)
- [x] `craftdesk_api/schemas/prompts.py` — Pydantic request/response schemas
- [x] `craftdesk_api/routers/prompts.py` — /scrape-etsy, /generate, and /jobs/{id}/export (.txt download) endpoints
- [x] `craftdesk_api/tests/test_prompts.py` — Pytest test suite for prompt studio backend
- [x] `craftdesk_web/src/app/prompt-studio/page.tsx` — Editorial Atelier UI with 4 input cards, Etsy scrape preview, prompt matrix, and one-click **"Export to .txt"** download button


## Step 6: Etsy OAuth PKCE Shop Connector ✅
- [x] `craftdesk_api/services/etsy_oauth.py` — Etsy Open API v3 OAuth 2.0 PKCE helper (code_verifier/challenge generator, auth URL, token exchange, shop details)
- [x] `craftdesk_api/schemas/etsy.py` — Pydantic request/response schemas
- [x] `craftdesk_api/routers/etsy.py` — /auth/url, /auth/callback (Fernet AES-256 encrypted storage in PostgreSQL), /shops list, and /shops/{id} disconnect endpoints
- [x] `craftdesk_api/tests/test_etsy.py` — 3 pytest tests passing (30/30 total backend tests green)
- [x] `craftdesk_web/src/app/shops/page.tsx` — Editorial Atelier UI for managing connected Etsy stores with PKCE authorization flow & AES-256 security banner


## Step 7: 6-Stage Pipeline + Failure States ✅
- [x] `craftdesk_api/schemas/pipeline.py` — Pydantic request/response schemas
- [x] `craftdesk_api/services/pipeline_runner.py` — 6-stage pipeline orchestrator (Image Gen, BG Removal, Upscale, Mockups, PDF, Metadata)
- [x] `craftdesk_api/routers/pipeline.py` — /jobs start, get, stages list, single-stage retry, and WebSocket progress stream endpoints
- [x] `craftdesk_api/tests/test_pipeline.py` — Pytest test suite (33/33 total backend tests green)
- [x] `craftdesk_web/src/app/pipeline/page.tsx` — Editorial Atelier UI with 6 stage status cards, animated progress bars, root exception box, stderr log viewer, and **"Retry Stage"** action


## Step 8: Full Mockup Gallery Review + Push to Etsy ✅
- [x] `craftdesk_api/schemas/review.py` — Pydantic request/response schemas
- [x] `craftdesk_api/services/etsy_publisher.py` — Etsy Open API v3 draft listing publisher with digital download taxonomy
- [x] `craftdesk_api/routers/review.py` — /review/{job_id} review payload, metadata update, and push-to-etsy draft creation endpoints
- [x] `craftdesk_api/tests/test_review.py` — 3 pytest tests passing (36/36 total backend tests green)
- [x] `craftdesk_web/src/app/review/[job_id]/page.tsx` — Editorial Atelier UI with Hero image showcase, full 4-mockup gallery grid, interactive Lightbox modal, PDF wrap download, inline metadata editor (title, description, 13 tags), and **"Push Draft Listing to Etsy Shop"** action button


## Step 9: Settings Page
- [ ] Profile update endpoints + UI
- [ ] GCP config upload (encrypted)
- [ ] API key management (encrypted)

## Step 10: End-to-End Integration Test
- [ ] Full pipeline run test (VM start → prompts → pipeline → review → Etsy push)
- [ ] `pytest` integration test suite
