# Plan: CraftDesk Phase 1 — Complete Consolidated Implementation

**Date:** 2026-07-24
**Status:** approved — SINGLE SOURCE OF TRUTH
**Related:** [plans/2026-07-24-craftdesk-saas-platform-architecture.md](file:///d:/Janesh/ETSY/ETSY-pipeline/plans/2026-07-24-craftdesk-saas-platform-architecture.md)

> Every feature discussed across the entire session is captured here.

---

## 1. Architectural Decisions

### A. Database: Dual-Database (Polyglot Persistence)

| Database | Owns | Why |
|:---|:---|:---|
| **MongoDB** (existing) | `prompt_jobs`, `pipeline_jobs`, stage logs, generated prompts | Already wired into all `etsy_pipeline` workers. Zero migration. |
| **PostgreSQL** (new) | `users`, `etsy_shops`, `gcp_configs`, `api_keys` | ACID, AES-256 encrypted OAuth tokens, relational joins. |

**Never migrate MongoDB data.** PostgreSQL only handles new CraftDesk SaaS user records.

### B. PostgreSQL Hosting — Self-hosted on Existing GCP VM (Recommended)

| Option | Monthly Cost | Notes |
|:---|:---|:---|
| **✅ Self-host on existing GCP VM (Docker)** | **$0 extra** | Use existing GPU VM. No added cost. Full control. |
| Neon.tech Free | $0 | 512 MB, auto-suspend compute. Good free fallback. |
| Supabase Free | $0 | Pauses after 7 days inactivity. Avoid in production. |
| GCP Cloud SQL | $7–15+/month | Overkill at this stage. |

**Decision: Run PostgreSQL in Docker on the single existing GCP GPU VM.**

### B. VM Architecture — ✅ Single GPU VM (Confirmed, Phase 1)

```
┌───────────────────────────────────────────────────────────┐
│               GCP GPU VM (Single Instance)                │
│                                                           │
│  ComfyUI (:8188) + ALL pipeline workers + FastAPI API     │
│                                                           │
│  Stages: 🎨 Image Gen → ✂️ BG Remove → 🔍 Upscale →     │
│          🖼️ Mockups → 📄 PDF → 📝 Metadata               │
│                                                           │
│  Start VM → run full pipeline → Stop VM (saves cost)      │
└───────────────────────────────────────────────────────────┘
              ↕ always-on (VM lifecycle independent)
┌──────────────────────────┐   ┌──────────────────────────┐
│  Neon.tech (PostgreSQL)  │   │  MongoDB (existing)       │
│  Users, auth, shops      │   │  Pipeline job state       │
└──────────────────────────┘   └──────────────────────────┘
```

- The single GPU VM runs ComfyUI, all `etsy_pipeline` workers, and the FastAPI backend together.
- **VM is started from the CraftDesk UI** via GCP Compute Engine API before running the pipeline.
- **VM is stopped from the CraftDesk UI** after pipeline completes — saves GCP cost.
- Neon.tech and MongoDB remain reachable at all times regardless of VM state.

> **Phase 2 upgrade:** Split GPU VM (image gen only) + cheap CPU VM (all other stages) to cut GPU idle cost. Deferred.

---

## 2. Frontend Design System (cluade-design.md)

> All UI code must follow `.agents/cluade-design.md` (frontend-design skill). No generic AI-template aesthetics.

| Token | Value | Use |
|:---|:---|:---|
| Obsidian | `#0B0F19` | Page background |
| Base | `#121A2D` | Card / panel background |
| Indigo | `#5850EC` | Primary CTA, active states |
| Violet | `#9061F9` | Accent highlights, hover glows |
| Emerald | `#10B981` | Success / Completed stage |
| Danger | `#EF4444` | Failed stage, error states |
| Warning | `#F59E0B` | Running / in-progress |
| Slate Border | `#1E293B` | Card borders, dividers |

Typography: `Outfit` (headings) + `Inter` (body) + `JetBrains Mono` (tags, code, logs, prompt text)

---

## 3. Complete Feature Set

### Feature 1: Authentication (`/login`, `/register`)
- Email + Password with `bcrypt` hashing
- JWT access + refresh tokens
- Protected routes → redirect to `/login`
- "Remember me" persistent session

### Feature 2: Dashboard (`/dashboard`)
- Overview cards: prompts generated, pipelines run, listings published
- Recent jobs table with status chips
- Quick actions: "New Prompt Set", "Run Pipeline", "View Shops"
- GPU VM status widget (read-only current state)

### Feature 3: Etsy Shop Connector (`/shops`)
- Connect shops via OAuth 2.0 PKCE flow
- AES-256 Fernet token storage in PostgreSQL
- Shop cards: name, avatar, listing count, last synced
- Disconnect shop / token auto-refresh

### Feature 4: Multi-Input AI Prompt Studio (`/prompt-studio`)

Inputs (any combination):
1. Theme Text — free-text, e.g. "Wonder Woman Birthday Watercolor"
2. Etsy Product URL — backend scrapes title, description, up to 5 thumbnail images
3. Reference Images — drag-drop upload (1–5 images) → Gemini 2.5 Flash Vision
4. Prompt Count — numeric target (e.g. 10, 22, 50)

Output + Export:
- Sectioned prompt matrix in JetBrains Mono
- "Export to .txt" downloads all prompts as plain text
- "Copy All" to clipboard
- "Export CSV" with prompt index + text

### Feature 5: GPU VM Manager (sidebar widget on `/pipeline`)

States: `Stopped 🔴` → `Starting... ⏳` → `Booting ComfyUI... ⚙️` → `Ready ✅`

Start flow:
1. `POST /api/v1/gcp/vm/start` → GCP Compute Engine `instances().start()`
2. Polls until VM status `RUNNING`
3. Health-checks `http://<vm-ip>:8188` until HTTP 200
4. WebSocket event `vm_ready` → Pipeline "Run" button activates

Post-pipeline: "Stop VM 🔴" → `instances().stop()` to save GCP costs.
One-time setup: Upload GCP Service Account JSON via `/settings/gcp`.

### Feature 6: 6-Stage Pipeline Progress Bar (`/pipeline`)

Button: **"Run CraftDesk Pipeline"** (active only when VM `Ready ✅`)

Per-stage states:
- `⏳ Pending` (grey)
- `⚡ Running` (blue animated pulse + %)
- `✅ Completed` (green)
- `❌ Failed` (red, expands to show):
  - Root error message (last exception or stderr) in JetBrains Mono
  - Stage name + failure timestamp
  - **"Retry Stage"** button — re-queues that stage only
  - **"View Full Log"** — collapsible scrollable full stderr panel

| Stage | Worker | Progress Metric | Failure Examples |
|:---|:---|:---|:---|
| 🎨 Image Generation | `ImageWorker` / ComfyUI | `done/total` images | OOM, GPU timeout, CUDA error |
| ✂️ Background Removal | `BackgroundRemovalWorker` | Files processed | rembg model error, VRAM |
| 🔍 AI Upscaling | `UpscaleWorker` | Files upscaled | Tile OOM, disk full |
| 🖼️ Mockup Creation | `MockupWorker` | Mockup PNGs rendered | Missing template, PIL error |
| 📄 PDF Generation | `MockupWorker` (PDF wrap) | Drive link created | Drive API auth failure |
| 📝 Metadata Generation | `MetadataWorker` | Title + 13 tags done | Gemini Vision error, parse fail |

### Feature 7: Full Mockup Gallery Review (`/review/:job_id`)

- **Hero.png** — full-width featured image at top
- **All mockup PNGs** — scrollable CSS grid showing every generated mockup (not just Hero)
- **Click-to-expand lightbox** — full-size view with download button per mockup
- **Etsy Listing Metadata** — inline-editable title, description, 13 tag chips
- **Shop selector** — choose which connected Etsy shop to publish to
- **"Push to Etsy Shop"** button → creates draft listing via Etsy Open API v3 → redirects to Etsy listing URL on success

### Feature 8: Settings (`/settings`)
- Profile: name, email, password change
- Etsy Shops: same as `/shops`
- GCP Config: upload/update service account JSON
- API Keys: Gemini, Replicate (stored encrypted)

---

## 4. Backend API Endpoints (Complete)

### Auth `/api/v1/auth`
- `POST /register` — Create user
- `POST /login` — Return JWT access + refresh
- `POST /refresh` — Refresh access token
- `POST /logout` — Invalidate refresh token

### Prompts `/api/v1/prompts`
- `POST /generate` — Multi-input prompt generation
- `GET /jobs/{job_id}` — Job status + results
- `GET /jobs/{job_id}/export` — Download `.txt` file

### Pipeline `/api/v1/pipeline`
- `POST /jobs` — Start pipeline job
- `GET /jobs/{job_id}` — Full job status
- `GET /jobs/{job_id}/stages` — Per-stage status, progress %, root error
- `POST /jobs/{job_id}/stages/{stage}/retry` — Retry one failed stage
- `WS /jobs/{job_id}/stream` — WebSocket for real-time stage progress events

### GCP VM `/api/v1/gcp`
- `POST /vm/start` — Start GCP VM
- `GET /vm/status` — VM status + ComfyUI health check at `:8188`
- `POST /vm/stop` — Stop VM
- `PUT /config` — Save encrypted GCP service account config

### Etsy `/api/v1/etsy`
- `GET /auth/url` — Generate PKCE OAuth URL
- `GET /auth/callback` — Handle callback, store encrypted tokens
- `GET /shops` — List connected shops
- `DELETE /shops/{shop_id}` — Disconnect shop
- `POST /shops/{shop_id}/listings` — Push listing to Etsy

### Review `/api/v1/review`
- `GET /jobs/{job_id}` — Hero.png URL + all mockup URLs + metadata
- `PATCH /jobs/{job_id}/metadata` — Update title/description/tags before publishing

---

## 5. Database Schema

### PostgreSQL (New SaaS records only)

```
users: id(UUID PK) | email(UNIQUE) | password_hash | full_name | created_at | updated_at

etsy_shops: id | user_id(FK) | shop_id | shop_name
            encrypted_access_token(AES-256) | encrypted_refresh_token(AES-256)
            token_expires_at | is_active

gcp_configs: id | user_id(FK) | project_id | zone | instance_name
             encrypted_service_account_json(AES-256) | comfy_ui_port(DEFAULT 8188)

api_keys: id | user_id(FK) | service(gemini/replicate)
          encrypted_api_key(AES-256) | created_at
```

### MongoDB (Existing — no changes)
- `prompt_jobs` — prompt generation state
- `pipeline_jobs` — stage logs, per-stage progress, stderr on failure
- `generated_assets` — file paths for images, mockups, PDFs per job

---

## 6. Frontend Routes

| Route | View |
|:---|:---|
| `/login` | Email + password login |
| `/register` | Create new account |
| `/dashboard` | Overview stats + recent jobs |
| `/prompt-studio` | Multi-input AI prompt generation |
| `/pipeline` | GPU VM widget + 6-stage progress bar |
| `/review/:job_id` | Full mockup gallery + metadata edit + Push to Etsy |
| `/shops` | Connect/manage Etsy shops |
| `/settings` | Profile, GCP config, API keys |

---

## 7. Ordered Implementation Steps

| Step | Task | Verify |
|:---|:---|:---|
| 1 | PostgreSQL + FastAPI backend — models, Alembic, AES-256, JWT auth | `pytest` auth tests pass. JWT + encryption round-trips. |
| 2 | Next.js 14 design system + auth pages `/login` `/register` | Pages render with correct palette/fonts. Auth flow works. Protected routes redirect. |
| 3 | Dashboard `/dashboard` — stats cards, recent jobs, VM status widget | Dashboard loads with real API data. |
| 4 | GCP VM Manager — API + ComfyUI health poller + UI widget | `POST /vm/start` starts GCP instance. Poller confirms ComfyUI ready at `:8188`. |
| 5 | Multi-Input Prompt Studio + `.txt` export | Text, URL scrape, image upload each generate prompts. Export downloads. |
| 6 | Etsy OAuth PKCE Shop Connector `/shops` | User connects shop. Token stored encrypted. Shop card appears. |
| 7 | 6-Stage Pipeline + Per-Stage Failure States | WebSocket streams events. ❌ Failed card shows root error + "Retry Stage" button. |
| 8 | Full Mockup Gallery Review + Lightbox + Push to Etsy | All mockups load in grid. Lightbox opens on click. Metadata inline-editable. Push creates Etsy draft listing. |
| 9 | Settings page `/settings` | GCP config saves + encrypts. API keys stored. Profile updates work. |
| 10 | End-to-End Integration Test | Full run: VM start → Prompts → Pipeline → Review all mockups → Edit metadata → Push to Etsy. Zero manual steps. |
