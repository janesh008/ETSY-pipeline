# CraftDesk API Backend — High-Level Architecture & Business Scope

## 🎯 Scope & Responsibility

`craftdesk_api` is the production FastAPI backend service powering the CraftDesk Etsy Automation SaaS platform. It handles user authentication, multi-tenant database management, GCP GPU VM automation, AI prompt synthesis, multi-tenant Etsy OAuth PKCE connections, 6-stage pipeline orchestration with failure retry logic, review gallery management, and Etsy API v3 draft listing publishing.

---

## 🏗️ Architectural Overview

```
                        ┌─────────────────────────────────────┐
                        │      CraftDesk Web Frontend         │
                        │    Next.js 14 (Editorial Atelier)   │
                        └──────────────────┬──────────────────┘
                                           │  HTTP REST / WebSockets
                                           ▼
                        ┌─────────────────────────────────────┐
                        │        FastAPI Application          │
                        │       (craftdesk_api/main.py)       │
                        └──────────────────┬──────────────────┘
                                           │
           ┌───────────────────────────────┼───────────────────────────────┐
           ▼                               ▼                               ▼
 ┌───────────────────┐           ┌───────────────────┐           ┌───────────────────┐
 │   Neon.tech DB    │           │  GCP Compute API  │           │   Gemini 2.5 API  │
 │ (PostgreSQL ORM)  │           │ (GPU VM Lifecyle) │           │ (Prompt Engine)   │
 └───────────────────┘           └───────────────────┘           └───────────────────┘
```

---

## 🔒 Security Model

1. **Password Hashing:** Uses `bcrypt` (cost factor 12) via `passlib`. Plaintext passwords are never stored.
2. **JWT Authentication:** Tokens are signed using HS256 with a 32-byte secret (`JWT_SECRET_KEY`).
   - Access Token expiration: 60 minutes
   - Refresh Token expiration: 30 days
3. **AES-256 Fernet Encryption:** All sensitive third-party keys are encrypted before hitting the Neon.tech database:
   - Etsy OAuth Access & Refresh tokens in `etsy_shops`
   - GCP Service Account JSON keys in `gcp_configs`
   - Gemini & Replicate API keys in `api_keys`

---

## 📊 Database Strategy

- **Neon.tech PostgreSQL (Async SQLAlchemy 2.0):** Stores relational account entities (`users`, `etsy_shops`, `gcp_configs`, `api_keys`).
- **SQLite (In-Memory `sqlite+aiosqlite`):** Used during `pytest` execution for isolated, high-speed test environments without requiring a live cloud connection.
- **MongoDB (Job State Storage):** Manages transient, high-volume pipeline job logs and stage states.

---

## ⚡ Core Business Flows

1. **Auth Flow:** `/register` → `/login` → Issue Access/Refresh Tokens.
2. **GPU VM Lifecycle Flow:** `/gcp/config` → `/gcp/vm/start` → Poll `/gcp/vm/status` + ComfyUI `:8188` health → `/gcp/vm/stop` (saves compute costs when idle).
3. **Prompt Generation Flow:** `/prompts/scrape-etsy` (extracts listing title/desc/images) → `/prompts/generate` (synthesizes via Gemini 2.5) → Download `/prompts/jobs/{id}/export` (`.txt` file).
4. **Etsy Store Connection Flow:** `/etsy/auth/url` (S256 PKCE challenge) → User approves on Etsy → `/etsy/auth/callback` (exchanges authorization code, encrypts tokens via AES-256 Fernet, saves shop).
5. **6-Stage Pipeline Flow:** `/pipeline/jobs` (starts Image Gen → BG Removal → 4x Upscaling → Mockup Creation → PDF Wrap → 300 DPI Metadata) → If stage fails, user inspects root exception and clicks `/pipeline/jobs/{id}/stages/{stage}/retry` to retry only the failed stage.
6. **Etsy Publishing Flow:** `/review/{id}` (inspects Hero image, 4 mockups, PDF wrap, and metadata) → `/review/{id}/metadata` (edits title, description, 13 tags) → `/review/{id}/push-to-etsy` (creates draft listing on Etsy via API v3).
