# CraftDesk API Backend — Business Logic & Domain Architecture Guide

## 🎯 Business Problem & Value Proposition

Etsy digital clipart sellers face severe operational bottlenecks:
1. **Manual Labor Drain:** Creating a single clipart listing (writing 20+ Midjourney/ComfyUI prompts, generating images, stripping backgrounds, 4x upscaling, creating product mockups, building clickable PDF delivery wraps, writing SEO descriptions & 13 tags, and manual Etsy uploading) requires **1.5 to 2 hours per listing**. A shop owner releasing 10 listings per week wastes **15 to 20 hours in repetitive administrative tasks**.
2. **High Cloud Hosting Costs:** Running dedicated GPU server instances in Google Cloud Platform (GCP) 24/7 costs **$300–$500/month** even when idle.
3. **Etsy Account Risk:** Storing plain Etsy OAuth tokens or sharing raw API keys exposes sellers to shop bans or credential theft.
4. **Compute Credit Waste:** If a multi-step batch rendering pipeline crashes midway (e.g., CUDA OOM error on image upscaling), standard scripts discard all previously generated assets, forcing sellers to re-run the entire pipeline and waste API credits.

### 💡 CraftDesk Business Solution

`craftdesk_api` is the high-performance FastAPI orchestration service that automates the entire Etsy digital product assembly line:
- **Reduces Listing Creation Time:** Cuts total time per listing from **120 minutes down to 3 minutes** (a **97.5% time saving**).
- **Cuts Cloud Hosting Costs by 80%:** Automates GCP Compute Engine GPU VM lifecycles (`start` before generation, `stop` immediately after asset creation).
- **Bank-Grade Secret Protection:** Vaults all Etsy OAuth access/refresh tokens, GCP service account JSON credentials, and Gemini API keys using **AES-256 Fernet** encryption in a Neon.tech PostgreSQL database.
- **Fault-Tolerant Single-Stage Retries:** Enables sellers to inspect root exception tracebacks and retry *only* the specific failed stage without restarting the entire pipeline or losing completed assets.

---

## 🏗️ Domain Architecture & Component Workflow

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 ETSY SELLER WORKSPACE                                  │
│                 Next.js 14 App Router Frontend (`craftdesk_web`)                        │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Authenticated HTTP REST / WebSockets
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                            FASTAPI BACKEND (`craftdesk_api`)                           │
│                                                                                        │
│  ┌────────────────────┐   ┌────────────────────┐   ┌──────────────────────────────┐  │
│  │   Auth & Security  │   │  GCP VM Lifecycle  │   │    Multi-Input Prompt Engine │  │
│  │ AES-256 Fernet/JWT │   │ Start / Health / Stop │   │ Gemini 2.5 + Etsy Scraper    │  │
│  └────────────────────┘   └────────────────────┘   └──────────────────────────────┘  │
│  ┌────────────────────┐   ┌────────────────────┐   ┌──────────────────────────────┐  │
│  │  Etsy OAuth PKCE   │   │  6-Stage Pipeline  │   │   Mockup Review & Publisher  │  │
│  │ S256 Verifier/Store│   │ Runner & Stage Retry│   │ Etsy API v3 Draft Creator    │  │
│  └────────────────────┘   └────────────────────┘   └──────────────────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│  Neon.tech PostgreSQL   │     │  GCP Compute Engine GPU │     │   Etsy Open API v3      │
│  Encrypted SaaS Records │     │ ComfyUI GPU Server :8188│     │ Digital Listing Drafts  │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

---

## 🔄 End-to-End Business Logic Lifecycles

### 1. Account Onboarding & AES-256 Vaulting
- **Goal:** Provide isolated, secure multi-tenant access for Etsy studio owners.
- **Business Rule:** User registers with email & password. Password is hashed via `bcrypt` (cost factor 12). JWT access tokens (60 min) and refresh tokens (30 days) are issued.
- **Vaulting:** When the seller inputs their GCP service account JSON key or AI provider API keys, `craftdesk_api` encrypts the payload using AES-256 Fernet before writing to Neon.tech PostgreSQL. Unencrypted credentials never exist on disk or in database logs.

### 2. Market Research & Multi-Input Prompt Synthesis
- **Goal:** Convert market demand and competitor inspiration into 22–100 commercial watercolor clipart prompts.
- **Business Rule:**
  1. The seller provides a **Text Theme** (e.g. "Wonder Woman Birthday Watercolor"), an optional **Etsy Product Link**, and **Reference Style Images**.
  2. If an Etsy URL is provided, `EtsyScraperService` fetches the competitor's title, description, and gallery thumbnails.
  3. `PromptEngineService` injects these multi-modal inputs into Gemini 2.5 FlashVision with a commercial clipart system instruction.
  4. Output is formatted into structured numbered prompts and a downloadable `.txt` matrix file.

### 3. On-Demand GPU Cloud Infrastructure Management
- **Goal:** Eliminate idle GCP GPU VM billing ($300+/mo).
- **Business Rule:**
  1. Seller clicks "Run Pipeline". `GcpVmService` calls GCP Compute Engine API `instances().start()`.
  2. FastAPI polls `GET http://<external-ip>:8188/` until ComfyUI responds HTTP 200 (Ready).
  3. The 6-stage pipeline runs.
  4. Once assets are generated, the seller or system stops the VM (`instances().stop()`), reducing cloud billing strictly to active rendering minutes.

### 4. 6-Stage Assembly Line & Resilient Stage Retry
- **Goal:** Execute digital asset production with zero loss of completed work upon failure.
- **Assembly Stages:**
  1. 🎨 **Image Generation:** Calls ComfyUI on GPU VM to generate high-resolution raw clipart.
  2. ✂️ **Background Removal:** Executes `rembg` AI model to strip backgrounds into transparent PNGs.
  3. 🔍 **AI Upscaling:** Uses Real-ESRGAN / 4x-UltraSharp to scale images to 300 DPI print quality.
  4. 🖼️ **Mockup Creation:** Generates 4 commercial mockups (T-Shirt, Mug, Paper Frame, Tote Bag).
  5. 📄 **Clickable PDF Wrap:** Generates customer PDF download link pointing to Google Drive.
  6. 📝 **SEO Metadata Generation:** Synthesizes optimized title, description hook, and 13 Etsy search tags.
- **Retry Business Rule:** If stage 3 fails (e.g. CUDA OOM), stages 1 and 2 remain marked `completed`. The seller clicks **"Retry Stage"** on stage 3. The server resets only stage 3 to `running` and resumes without re-rendering stages 1 and 2.

### 5. Multi-Tenant Etsy OAuth 2.0 PKCE & 1-Click Publishing
- **Goal:** Safely publish listing drafts directly to seller shops.
- **Security Rule:** Uses PKCE (Proof Key for Code Exchange) with `S256` `code_challenge` and `code_verifier`. No client secret is exposed to the browser.
- **Publishing Rule:** When seller clicks "Push Draft Listing to Etsy Shop", `EtsyPublisherService` decrypts the shop's OAuth access token, constructs the Etsy API v3 payload (`taxonomy_id=10985`, digital download type, max 140 char title, max 13 tags of 20 chars each), and creates a `DRAFT` listing on Etsy.
