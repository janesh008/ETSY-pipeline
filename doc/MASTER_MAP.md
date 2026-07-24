# Etsy Pipeline & CraftDesk SaaS — Master Project Map

Welcome! This document is a non-technical, friendly guide designed to help anyone (whether you are an AI agent, a developer, or a non-technical team member) understand exactly how this project works, what each part does, and how to make changes or solve bugs.

---

## 🗺️ Visual Project Map & Clickable Links

Use these links to jump directly to any directory or file in the codebase:

*   [**📁 Project Root Directory**](file:///d:/Janesh/ETSY/ETSY-pipeline)
    *   [📄 pyproject.toml](file:///d:/Janesh/ETSY/ETSY-pipeline/pyproject.toml) — Project dependencies and tool settings.
    *   [📄 AGENTS.md](file:///d:/Janesh/ETSY/ETSY-pipeline/AGENTS.md) — Workflow instructions for AI coding assistants.
    *   [📄 README.md](file:///d:/Janesh/ETSY/ETSY-pipeline/README.md) — Main GitHub setup guide.

*   [**📁 CraftDesk API Backend (`craftdesk_api`)**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api)
    *   [**📁 doc/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc) — Backend Documentation Layer
        *   [📄 HIGH_LEVEL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/HIGH_LEVEL.md) — Non-technical scope, security, and DB design.
        *   [📄 SKILL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/SKILL.md) — Coding guidelines, Gotchas, and testing rules.
        *   [📄 DETAILED.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/DETAILED.md) — Module specification & code structure.
    *   [**📁 core/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/core) — Application settings & security helpers.
        *   [📄 config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/core/config.py) — Pydantic Settings schema.
        *   [📄 security.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/core/security.py) — AES-256 Fernet encryption, bcrypt, JWT.
    *   [**📁 db/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/db) — SQLAlchemy async database base & session dependency.
        *   [📄 base.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/db/base.py) — Neon.tech engine & get_db.
    *   [**📁 models/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/models) — Database ORM models.
        *   [📄 user.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/models/user.py) — User model (users table).
        *   [📄 etsy_shop.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/models/etsy_shop.py) — EtsyShop model (etsy_shops table).
        *   [📄 gcp_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/models/gcp_config.py) — GcpConfig model (gcp_configs table).
        *   [📄 api_key.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/models/api_key.py) — ApiKey model (api_keys table).
    *   [**📁 schemas/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas) — Pydantic request/response schemas.
        *   [📄 auth.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/auth.py) — Auth payloads.
        *   [📄 gcp.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/gcp.py) — GCP VM payloads.
        *   [📄 prompts.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/prompts.py) — Prompt Studio payloads.
        *   [📄 etsy.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/etsy.py) — Etsy OAuth PKCE payloads.
        *   [📄 pipeline.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/pipeline.py) — 6-Stage Pipeline payloads.
        *   [📄 review.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/review.py) — Review & Publishing payloads.
        *   [📄 settings.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/settings.py) — Settings payloads.
    *   [**📁 services/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services) — Business logic services.
        *   [📄 gcp_vm.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/gcp_vm.py) — GCP Compute API & ComfyUI health poller.
        *   [📄 etsy_scraper.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_scraper.py) — Etsy listing URL scraper.
        *   [📄 prompt_engine.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/prompt_engine.py) — Gemini 2.5 Flash prompt synthesis.
        *   [📄 etsy_oauth.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_oauth.py) — Etsy OAuth 2.0 PKCE helper.
        *   [📄 pipeline_runner.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/pipeline_runner.py) — 6-stage pipeline orchestrator.
        *   [📄 etsy_publisher.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_publisher.py) — Etsy API v3 draft listing publisher.
    *   [**📁 routers/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers) — FastAPI route endpoints.
        *   [📄 auth.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/auth.py) — /register, /login, /refresh, /logout.
        *   [📄 gcp.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/gcp.py) — /gcp/config, /gcp/vm/start, /gcp/vm/stop, /gcp/vm/status.
        *   [📄 prompts.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/prompts.py) — /prompts/scrape-etsy, /prompts/generate, .txt export.
        *   [📄 etsy.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/etsy.py) — /etsy/auth/url, /etsy/auth/callback, /etsy/shops.
        *   [📄 pipeline.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/pipeline.py) — /pipeline/jobs, single-stage retry, WS stream.
        *   [📄 review.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/review.py) — /review/{id}, metadata patch, push-to-etsy.
        *   [📄 settings.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/settings.py) — /settings/profile, /settings/api-keys.
    *   [**📁 tests/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests) — Pytest suite (39 passing tests).
        *   [📄 conftest.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/conftest.py) — Shared aiosqlite test database fixture.
        *   [📄 test_auth.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/test_auth.py) — Auth unit tests.
        *   [📄 test_gcp.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/test_gcp.py) — GCP router tests.
        *   [📄 test_prompts.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/test_prompts.py) — Prompt Studio tests.
        *   [📄 test_etsy.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/test_etsy.py) — Etsy OAuth tests.
        *   [📄 test_pipeline.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/test_pipeline.py) — Pipeline runner tests.
        *   [📄 test_review.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/test_review.py) — Review & publishing tests.
        *   [📄 test_settings.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/tests/test_settings.py) — Settings tests.
    *   [📄 main.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/main.py) — FastAPI entry point.

*   [**📁 CraftDesk Web Frontend (`craftdesk_web`)**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web)
    *   [**📁 doc/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/doc) — Frontend Documentation Layer
        *   [📄 HIGH_LEVEL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/doc/HIGH_LEVEL.md) — Atelier design system & session lifecycle.
        *   [📄 SKILL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/doc/SKILL.md) — Client component rules, token mappings, and Gotchas.
        *   [📄 DETAILED.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/doc/DETAILED.md) — 11 Page component specifications.
    *   [**📁 src/app/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app) — App Router pages & CSS.
        *   [📄 globals.css](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/globals.css) — Editorial Atelier theme CSS tokens (#F7F6F0).
        *   [📄 layout.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/layout.tsx) — Outfit/Inter/Mono fonts & AuthProvider.
        *   [📄 page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/page.tsx) — Auth redirect landing page.
        *   [📄 login/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/login/page.tsx) — Login page.
        *   [📄 register/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/register/page.tsx) — Account registration page.
        *   [📄 dashboard/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/dashboard/page.tsx) — Studio dashboard & GPU VM widget.
        *   [📄 prompt-studio/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/prompt-studio/page.tsx) — AI Prompt Studio & .txt Exporter.
        *   [📄 shops/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/shops/page.tsx) — Etsy OAuth PKCE Shop Connector.
        *   [📄 pipeline/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/pipeline/page.tsx) — 6-Stage Pipeline & Failure Retry Card.
        *   [📄 review/[job_id]/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/review/%5Bjob_id%5D/page.tsx) — Mockup review, Lightbox modal & Etsy Publisher.
        *   [📄 settings/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/settings/page.tsx) — Studio settings & key store.
    *   [**📁 src/context/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/context) — State providers.
        *   [📄 AuthContext.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/context/AuthContext.tsx) — Session state & token storage.
    *   [**📁 src/lib/**](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/lib) — API utilities.
        *   [📄 api.ts](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/lib/api.ts) — TypeScript fetch client.

*   [**📁 Core Pipeline Package (`etsy_pipeline`)**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline)
    *   [📄 __init__.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/__init__.py) — Package entry point.
    *   [**📁 config/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/config) — System settings and env-var validation.
    *   [**📁 models/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/models) — Shared data structures (`job.py`).
    *   [**📁 pipeline/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/pipeline) — Sequencer (`orchestrator.py`).
    *   [**📁 workers/**](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers) — Stage implementations (`prompt_worker`, `image_worker`, `bg_removal_worker`, `upscale_worker`).
