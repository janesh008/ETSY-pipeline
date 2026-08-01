# Plan: Etsy Shop Connector — Multi-Shop Manager & Direct Listing Upload

**Date:** 2026-07-31
**Status:** approved
**Scope:** craftdesk_api + craftdesk_web (Etsy multi-shop publish dashboard)

---

## Problem Statement

The current `/shops` page is a flat list with no shop interaction. We need:
1. Each shop card clickable -> opens a Shop Publish Dashboard
2. A Connect New Shop button that kicks off real Etsy OAuth PKCE redirect
3. Inside the dashboard: 3 listing-upload modes (GCS bucket browser, manual upload, AI metadata generation)
4. One-click publish to Etsy (text + mockup images + PDF digital asset)

---

## Architecture Decisions

| Component | Specification |
|-----------|---------------|
| **Shop Credentials Storage** | Stored securely in database (`EtsyShop` model with Fernet AES-256 encrypted access & refresh tokens) per user. |
| **GCS Metadata Format** | Option 1 reads pre-validated `metadata/listing.json` directly (generated in Stage 6). Raw text parsing for `.txt` is completely removed. |
| **Multi-Shop GCS Pathing** | Non-pipeline uploads (Option 2 & 3) store assets in scalable per-shop GCS prefixes: `EtsyShops/{shop_name}/{date_folder}/{theme_slug}/` (separate from `Clipart/`). |
| **Image + PDF Upload to Etsy** | Reuses `EtsyWorker._upload_listing_images()` and `EtsyWorker._create_draft_listing()`, plus PDF digital file upload via Etsy `/listings/{id}/files` endpoint. |
| **AI Generation (Option 3)** | Uses Vertex AI `google.genai` + `MASTER_PROMPT_PATH` to output standard `listing.json` format directly. |

---

## Architecture Overview

### Frontend Pages
```
/shops                          <- MODIFY: clickable shop cards + real OAuth button
/shops/callback                 <- NEW: OAuth code exchange handler
/shops/[shop_id]/publish        <- NEW: 3-mode shop publish dashboard
```

### New Backend Endpoints
```
GET  /api/v1/etsy/gcs-folders
POST /api/v1/etsy/shops/{shop_db_id}/gcs-listing
POST /api/v1/etsy/shops/{shop_db_id}/upload-listing
POST /api/v1/etsy/shops/{shop_db_id}/generate-metadata
```

---

## File Change List

| Action | File |
|--------|------|
| MODIFY | `craftdesk_api/schemas/etsy.py` — 5 new Pydantic models |
| NEW | `craftdesk_api/services/etsy_listing_service.py` — orchestration service |
| MODIFY | `craftdesk_api/routers/etsy.py` — 4 new endpoints |
| MODIFY | `craftdesk_web/src/app/shops/page.tsx` — clickable cards + real OAuth redirect |
| NEW | `craftdesk_web/src/app/shops/callback/page.tsx` — OAuth callback handler |
| NEW | `craftdesk_web/src/app/shops/[shop_id]/publish/page.tsx` — 3-mode publish dashboard |
| MODIFY | `craftdesk_api/doc/DETAILED.md` |
| MODIFY | `doc/MASTER_MAP.md` |

---

## Implementation Order

1. Schemas — `craftdesk_api/schemas/etsy.py`
2. EtsyListingService — `craftdesk_api/services/etsy_listing_service.py`
3. Router — `craftdesk_api/routers/etsy.py` (4 new endpoints)
4. Frontend: `shops/page.tsx` (real OAuth + clickable cards)
5. Frontend: `shops/callback/page.tsx`
6. Frontend: `shops/[shop_id]/publish/page.tsx`
7. Docs — `DETAILED.md`, `MASTER_MAP.md`
8. Verification & Lint — `pytest`, `ruff check . --fix`
