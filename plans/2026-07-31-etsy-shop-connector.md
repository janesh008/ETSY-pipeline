# Plan: Etsy Shop Connector — Multi-Shop Manager & Direct Listing Upload

**Date:** 2026-07-31
**Status:** approved
**Related:** `plans/2026-07-31-replace-csv-with-per-theme-json.md` (listing.json fast-path integration)

---

## Problem Statement

The current `/shops` page is a flat list with no shop interaction. We need:
1. Each shop card clickable -> opens a Shop Publish Dashboard
2. A Connect New Shop button that kicks off real Etsy OAuth PKCE redirect
3. Inside the dashboard: 3 listing-upload modes (GCS bucket browser, manual upload, AI metadata generation)
4. One-click publish to Etsy (text + mockup images + PDF digital asset)

---

## Confirmed Decisions

| Question | Answer |
|----------|--------|
| GCS metadata auto-load + clean | Yes — auto-load listing.json (fast path) or raw_response.txt (slow path, cleaned via MetadataWorker._parse_and_validate_response()) |
| Image + PDF upload to Etsy | Yes — reuse EtsyWorker._upload_listing_images() and _create_draft_listing() patterns |
| Gemini method for Option 3 | Same Vertex AI google.genai + MASTER_PROMPT_PATH system prompt as MetadataWorker._call_gemini_vision() |
| Connect Shop button | Real PKCE OAuth redirect (window.location.href = auth_url) — replace setTimeout simulation |

---

## Architecture

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
| NEW | `craftdesk_api/services/etsy_listing_service.py` |
| MODIFY | `craftdesk_api/routers/etsy.py` — 4 new endpoints |
| MODIFY | `craftdesk_web/src/app/shops/page.tsx` — clickable cards + real OAuth redirect |
| NEW | `craftdesk_web/src/app/shops/callback/page.tsx` |
| NEW | `craftdesk_web/src/app/shops/[shop_id]/publish/page.tsx` |
| MODIFY | `craftdesk_api/doc/DETAILED.md` |
| MODIFY | `doc/MASTER_MAP.md` |

---

## Key Design Points

### EtsyListingService methods
- `list_gcs_folders()` — calls is_gcp_available(); enumerates Clipart/<date>/<slug>/ prefixes
- `load_and_clean_gcs_metadata()` — fast path: listing.json; fallback: raw_response.txt + _parse_and_validate_response()
- `publish_from_gcs()` — load metadata, create listing, upload mockups (Hero first), upload PDF, activate
- `publish_from_upload()` — take multipart bytes, create listing, upload images, upload PDF, activate
- `generate_metadata_from_mockups()` — Vertex AI Gemini Vision + MetadataWorker parser
- `_create_etsy_listing()` — mirrors EtsyWorker._create_draft_listing()
- `_upload_mockup_images()` — mirrors EtsyWorker._upload_listing_images()
- `_upload_digital_file()` — POST /shops/{id}/listings/{lid}/files (new, non-fatal)

### OAuth Connect Shop (real flow)
1. GET /etsy/auth/url -> { auth_url, code_verifier }
2. sessionStorage.setItem("etsy_code_verifier", code_verifier)
3. window.location.href = auth_url
4. Etsy redirects to /shops/callback?code=...&state=...
5. callback/page.tsx: POST /etsy/auth/callback -> success -> router.push('/shops')

---

## Implementation Steps

1. Schemas — craftdesk_api/schemas/etsy.py
2. EtsyListingService — craftdesk_api/services/etsy_listing_service.py
3. Router — craftdesk_api/routers/etsy.py (4 new endpoints)
4. Frontend: shops/page.tsx (real OAuth + clickable cards)
5. Frontend: shops/callback/page.tsx
6. Frontend: shops/[shop_id]/publish/page.tsx
7. Docs — DETAILED.md, MASTER_MAP.md
8. pytest craftdesk_api/tests/test_etsy.py -v
9. ruff check . --fix && ruff format .

---

## Verification Plan

1. /shops — Connect button -> browser redirects to Etsy OAuth (real, not setTimeout)
2. Etsy returns to /shops/callback -> spinner -> success -> /shops with new shop
3. Click shop card -> /shops/<id>/publish
4. Option 1: GCS available -> folder list; unavailable -> graceful notice
5. Option 2: upload mockups + PDF + fill form -> Publish -> Etsy link
6. Option 3: upload mockups -> Generate -> metadata fills -> Publish -> Etsy link
