# Plan: CraftDesk — AI-Powered Etsy Automation & Management SaaS Platform

**Date:** 2026-07-24
**Company / Product Name:** CraftDesk
**Status:** approved
**Related:** [doc/ARCHITECTURE.md](file:///d:/Janesh/ETSY/ETSY-pipeline/doc/ARCHITECTURE.md)

---

## Executive Summary
CraftDesk is an end-to-end multi-tenant SaaS platform built for digital asset creators and Etsy shop owners. It unifies AI prompt & asset bundle generation, bulk Etsy listing upload & publishing, automated AI listing management (bulk price & tag updates), and AI-driven shop analytics & next-listing recommendations into one seamless platform.

---

## Architecture & Tech Stack

### Frontend & UI Design System
- **Framework:** Next.js (React) + TypeScript
- **Styling & Design Guidance:** Directly governed by [.agents/cluade-design.md](file:///d:/Janesh/ETSY/ETSY-pipeline/.agents/cluade-design.md) (`frontend-design` skill).
- **Design Philosophy:** Distinctive, deliberate visual design tailored specifically to CraftDesk's human brief. Avoids generic AI template defaults, uses opinionated color palettes (4-6 named hex values), custom typography pairing, restrained motion, and functional UI copy.

### Backend & AI Engine
- **Backend Service:** FastAPI (Python 3.12+) — natively integrates existing `etsy_pipeline` workers (`prompt_worker`, `metadata_worker`, `etsy_worker`).
- **Task Queue:** Celery + Redis for asynchronous background batch operations (rate-limited Etsy bulk uploads, bulk price updates).
- **Database:** PostgreSQL (User authentication, Multi-tenant Etsy Shop OAuth Tokens encrypted with AES-256, Subscription Tiers) + Redis (Cache & Active Job State).
- **Integrations:** Etsy Open API v3 (OAuth 2.0 PKCE), Gemini 2.5/Vision API.

---

## Multi-Phase Roadmap

### Phase 1: Core Platform MVP & Authentication
1. **CraftDesk Branding & Design System:** Modern dashboard UI, navigation, theme tokens.
2. **User Authentication:** Email/Password & Social OAuth via NextAuth / Supabase Auth.
3. **AI Prompt Generator Module:** Form UI -> FastAPI endpoint executing `PromptWorker` -> interactive editable prompt matrix.
4. **Etsy OAuth 2.0 Store Connector:** OAuth authorization flow storing multi-tenant encrypted shop tokens.
5. **Bulk Listing Uploader Module:** Batch upload listings directly to Etsy API via `etsy_worker`.

### Phase 2: AI Shop Manager & Bulk Automation
1. Active shop inventory syncing from Etsy Open API.
2. Bulk listing selector & AI bulk editor (price modifications, tag refreshes, title optimizations across 200+ listings).
3. Background rate-limited queue execution.

### Phase 3: Analytics & Next Listing Recommendation Engine
1. Shop performance stats dashboard (views, favorites, conversion rate analysis).
2. AI Niche Scanner recommending profitable upcoming bundle themes.

---

## Verification & Phased Execution
Each phase will be developed, tested, and verified sequentially with user feedback before progressing to subsequent phases.
