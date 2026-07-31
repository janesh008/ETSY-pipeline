# Etsy Shop Connector — Multi-Shop Manager & Direct Listing Upload

**Updated:** 2026-07-31 after user clarifications

---

## Problem Statement

The current `/shops` page is a flat list with no shop interaction. We need:
1. Each shop card clickable → opens a **Shop Publish Dashboard**
2. A **Connect New Shop** button on the shops list that kicks off Etsy OAuth PKCE redirect
3. Inside the dashboard: 3 listing-upload modes (GCS bucket browser, manual upload, AI metadata generation)
4. One-click publish to Etsy (text + mockup images + PDF digital asset)

---

## Confirmed Decisions (from user review)

| Question | Answer |
|----------|--------|
| GCS metadata auto-load + clean | Yes — auto-load `metadata/raw_response.txt`, **clean it** through `MetadataWorker._parse_and_validate_response()` before showing |
| Image + PDF upload to Etsy | Yes — reuse `EtsyWorker._upload_listing_images()` and `EtsyWorker._create_draft_listing()` patterns directly |
| Gemini method for Option 3 | Same Vertex AI `google.genai` + `MASTER_PROMPT_PATH` system prompt as `MetadataWorker._call_gemini_vision()` |
| Connect Shop button | New "Connect Etsy Shop" button on `/shops` that triggers PKCE OAuth redirect to Etsy (already partially wired, needs real redirect instead of simulated) |

---

## Architecture Overview

### Two-Page Structure (Frontend)

```
/shops                          ← MODIFY: clickable shop cards + real "Connect Shop" OAuth button
/shops/[shop_id]/publish        ← NEW: 3-mode shop publish dashboard
```

### 4 New Backend API Endpoints

```
GET  /api/v1/etsy/gcs-folders                          ← list GCS Clipart/<date>/<slug>/ folders
POST /api/v1/etsy/shops/{shop_db_id}/gcs-listing       ← publish from GCS folder
POST /api/v1/etsy/shops/{shop_db_id}/upload-listing    ← publish from file upload
POST /api/v1/etsy/shops/{shop_db_id}/generate-metadata ← AI metadata from mockup images
```

---

## Proposed Changes

---

### 1. Backend — New Pydantic Schemas

#### [MODIFY] [etsy.py schemas](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/etsy.py)

Add the following models:

```python
class GcsFolderItem(BaseModel):
    gcs_prefix: str            # e.g. "Clipart/2026-07-22/Wonder_Woman/"
    date_folder: str           # e.g. "2026-07-22"
    theme_slug: str            # e.g. "Wonder_Woman"
    display_name: str          # human-friendly slug (underscores → spaces)
    has_mockups: bool
    has_pdf: bool
    has_metadata: bool         # True if metadata/raw_response.txt exists

class GcsFolderListResponse(BaseModel):
    folders: list[GcsFolderItem]
    gcs_available: bool        # False if running locally without GCS credentials

class GcsListingRequest(BaseModel):
    gcs_prefix: str            # Which GCS folder to publish from
    title: str | None = None   # Override; if None, loaded from metadata or slug
    description: str | None = None
    tags: list[str] = []
    price: float = 5.99
    quantity: int = 999

class GenerateMetadataResponse(BaseModel):
    title: str
    description: str
    tags: list[str]

class ListingPublishResponse(BaseModel):
    listing_id: str
    etsy_listing_url: str
    status: str                # "active" or "draft"
    shop_name: str
    images_uploaded: int
    pdf_uploaded: bool
    message: str
```

---

### 2. Backend — New Service

#### [NEW] [etsy_listing_service.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_listing_service.py)

**Responsibilities:**
- Browse GCS folders for the publish dashboard (Option 1)
- Orchestrate listing creation + image upload + PDF digital asset upload for all 3 modes
- Generate metadata from mockup images via Gemini Vision (Option 3)

**Key methods and how they work:**

```
EtsyListingService
│
├── list_gcs_folders(settings) -> GcsFolderListResponse
│   • Calls is_gcp_available() — if False, returns gcs_available=False + empty list
│   • Uses GCSStore.list_objects("Clipart/") to enumerate prefixes at depth 3:
│       Clipart/<date>/<theme_slug>/
│   • For each folder, checks for sub-prefixes: mockups/, pdf/, metadata/
│   • Returns sorted list (newest date first)
│
├── load_and_clean_gcs_metadata(gcs_prefix, settings) -> dict | None
│   • Downloads gs://bucket/<gcs_prefix>metadata/raw_response.txt via GCSStore
│   • Pipes raw text through MetadataWorker._parse_and_validate_response()
│     to strip vague/template text and extract clean title, description, 13 tags
│   • Returns { title, description, tags } or None if file not present
│
├── publish_from_gcs(shop_id, shop_name, access_token, gcs_prefix, overrides, settings) -> dict
│   • Loads clean metadata via load_and_clean_gcs_metadata()
│   • Merges with any overrides from the UI form
│   • Calls _create_etsy_listing() to create the draft text listing
│   • Downloads mockup PNGs from GCS to a temp dir, sorted Hero.png first
│   • Calls _upload_mockup_images() (mirrors EtsyWorker._upload_listing_images())
│   • Downloads PDF from GCS, calls _upload_digital_file()
│   • Calls _publish_listing() to set state=active
│   • Returns ListingPublishResponse
│
├── publish_from_upload(shop_id, shop_name, access_token, mockup_files, pdf_file, meta) -> dict
│   • Takes raw UploadFile bytes from multipart form
│   • Calls _create_etsy_listing() with provided metadata
│   • Saves image bytes to a temp dir, calls _upload_mockup_images()
│   • Calls _upload_digital_file() with the PDF bytes
│   • Calls _publish_listing()
│   • Returns ListingPublishResponse
│
├── generate_metadata_from_mockups(mockup_files, theme_hint, settings) -> dict
│   • Reuses MetadataWorker._call_gemini_vision() pattern exactly:
│     - Instantiates google.genai.Client(vertexai=True, project=..., location=...)
│     - Reads MASTER_PROMPT_PATH system instruction file
│     - Sends up to 5 image bytes as types.Part.from_bytes()
│   • Passes raw Gemini response through MetadataWorker._parse_and_validate_response()
│     to strip vague/template text from the AI output
│   • Returns { title, description, tags }
│
├── _create_etsy_listing(shop_id, access_token, title, description, tags, price, qty) -> tuple[int, str]
│   • Mirrors EtsyWorker._create_draft_listing() logic exactly:
│     - Fetches taxonomy_id via GET /seller-taxonomy/nodes (looks for "clip art")
│     - POSTs to POST /shops/{shop_id}/listings with is_digital=True, type="download"
│   • Returns (listing_id, listing_url)
│
├── _upload_mockup_images(shop_id, listing_id, access_token, image_paths) -> int
│   • Mirrors EtsyWorker._upload_listing_images() exactly:
│     - sort_mockup_images() — Hero.png first
│     - POST /shops/{shop_id}/listings/{listing_id}/images per image (max 10)
│   • Returns count of successfully uploaded images
│
└── _upload_digital_file(shop_id, listing_id, access_token, pdf_path_or_bytes, filename) -> bool
    • POST /shops/{shop_id}/listings/{listing_id}/files
    • Uploads the PDF as the downloadable digital asset
    • Returns True on success, False on failure (non-fatal)
```

> [!IMPORTANT]
> **No new Etsy API logic is invented here.** The `_create_etsy_listing`, `_upload_mockup_images`, and `_publish_listing` methods directly mirror the battle-tested patterns in `EtsyWorker`. The metadata cleaning in Option 1 and Option 3 both reuse `MetadataWorker._parse_and_validate_response()` unchanged.

> [!NOTE]
> The Etsy digital file upload endpoint is `POST /v3/application/shops/{shop_id}/listings/{listing_id}/files`. This is a multipart upload distinct from the image upload. It attaches the actual PDF the buyer downloads. This is a new capability not yet in `etsy_publisher.py`.

---

### 3. Backend — Router Changes

#### [MODIFY] [etsy.py router](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/etsy.py)

Add 4 new endpoints to the existing `/etsy` router prefix. **No existing endpoints are modified.**

```
GET  /etsy/gcs-folders
     Auth: Bearer JWT
     → calls EtsyListingService.list_gcs_folders(settings)
     → returns GcsFolderListResponse

POST /etsy/shops/{shop_db_id}/gcs-listing
     Auth: Bearer JWT
     Body: GcsListingRequest (JSON)
     → fetches shop row from DB, decrypts access_token via Fernet
     → calls EtsyListingService.publish_from_gcs()
     → returns ListingPublishResponse

POST /etsy/shops/{shop_db_id}/upload-listing
     Auth: Bearer JWT
     Body: multipart/form-data
       - mockup_files: list[UploadFile]  (PNG/JPG, max 10)
       - pdf_file: UploadFile            (PDF)
       - title: str
       - description: str
       - tags: str                       (comma-separated, max 13)
       - price: float
       - quantity: int
     → calls EtsyListingService.publish_from_upload()
     → returns ListingPublishResponse

POST /etsy/shops/{shop_db_id}/generate-metadata
     Auth: Bearer JWT
     Body: multipart/form-data
       - mockup_files: list[UploadFile]  (PNG/JPG, up to 5)
       - theme_hint: str | None
     → calls EtsyListingService.generate_metadata_from_mockups()
     → returns GenerateMetadataResponse
```

---

### 4. Frontend — Shops List Page

#### [MODIFY] [shops/page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/shops/page.tsx)

Two targeted changes:

**A. Real "Connect Etsy Shop" OAuth redirect** (fix existing simulated flow):
- The current `handleConnectShop` simulates OAuth via a `setTimeout` demo. Replace this with a **real PKCE redirect**:
  1. Call `GET /etsy/auth/url` → get `{ auth_url, code_verifier }` 
  2. Save `code_verifier` to `sessionStorage`
  3. `window.location.href = auth_url` → redirects user to Etsy consent page
  4. Etsy redirects back to `/shops/callback` with `?code=...&state=...`
  5. A new `shops/callback/page.tsx` picks up the code, calls `POST /etsy/auth/callback`, then redirects to `/shops`

**B. Clickable shop cards:**
- Each shop card becomes a `<Link href={/shops/${shop.id}/publish}>` wrapper
- Add a visible `→ Open Shop Dashboard` CTA button (terracotta/orange, right side of card)
- Keep existing Disconnect and ExternalLink buttons intact (stop propagation on click)

---

### 5. Frontend — OAuth Callback Page (NEW)

#### [NEW] `shops/callback/page.tsx`

A minimal page that:
1. Reads `?code=` and `?state=` from the URL
2. Reads `etsy_code_verifier` from `sessionStorage`
3. POSTs to `POST /api/v1/etsy/auth/callback` with `{ code, code_verifier, redirect_uri }`
4. On success → `router.push('/shops')` with a success toast
5. Shows a loading spinner while the exchange is in progress
6. Shows error if exchange fails

---

### 6. Frontend — Shop Publish Dashboard (NEW)

#### [NEW] `shops/[shop_id]/publish/page.tsx`

A rich single-page dashboard with three tab-mode cards.

**Page-level data fetching on load:**
- Fetch the specific shop details: `GET /etsy/shops` → find shop by `shop_id` param
- If Option 1 selected: fetch GCS folders from `GET /etsy/gcs-folders`

**Header:**
```
← Back to Shops  |  🏪 <ShopName>  |  "Upload Listing" badge
```

**Mode Tab Switcher** (pill tabs, Atelier design style):
```
[📁 GCS Bucket]  [⬆ Manual Upload]  [✨ AI Generate]
```

---

**Option 1 — GCS Bucket Browser:**
```
If gcs_available = false:
  ⚠️  "GCS not available in this environment. Configure GOOGLE_APPLICATION_CREDENTIALS to browse."

If gcs_available = true:
  Scrollable folder list (card per theme):
    📅 2026-07-22  |  Wonder Woman Birthday
    Icons: 🖼 Mockups  📄 PDF  🏷 Metadata  (greyed out if not present)
    [Select →] button

  On folder select → auto-loads metadata from backend (if has_metadata=true)
  → pre-fills the Listing Preview Panel below
```

**Option 2 — Manual Upload:**
```
┌─────────────────────────────┐
│  🖼 Drop Mockup Images      │
│  (up to 10 PNG/JPG)         │
└─────────────────────────────┘
┌─────────────────────────────┐
│  📄 Drop PDF Digital Asset  │
└─────────────────────────────┘
Manual form:
  Title (text input, 140 char limit)
  Description (textarea)
  Tags (pill input, max 13 tags, max 20 chars each)
  Price ($) | Quantity
→ auto-fills Listing Preview Panel
```

**Option 3 — AI Metadata Generation:**
```
┌─────────────────────────────┐
│  🖼 Drop Mockup Images      │
│  (up to 5 PNG/JPG)          │
└─────────────────────────────┘
┌─────────────────────────────┐
│  📄 Drop PDF Digital Asset  │
└─────────────────────────────┘
  Theme hint (optional text input): "Wonder Woman Birthday"
  [✨ Generate Metadata with Gemini]
  → loading spinner during generation
  → on success: auto-fills Listing Preview Panel
```

**Shared Listing Preview Panel** (bottom of page, always visible):
```
┌─ Listing Preview ─────────────────────────────────────────────────┐
│  Title: [editable input — max 140 chars]                          │
│  Description: [editable textarea]                                  │
│  Tags: [pill editor — 13 pills max, 20 chars each]                │
│  Price: $[____]   Quantity: [____]                                │
│  Mockup Thumbnails: [grid of 4–10 image previews]                 │
│  PDF: [filename badge if uploaded]                                │
└──────────────────────────────────────────────────────────────────┘
[🚀 Publish to Etsy]  ← disabled until at least title + 1 mockup present
```

**Post-publish success state:**
```
✅ Listing published!
   "Wonder Woman Birthday" has been pushed live to <ShopName>
   [🔗 View on Etsy →]  [← Back to Shops]
```

---

### 7. Documentation

#### [MODIFY] [craftdesk_api/doc/DETAILED.md](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/DETAILED.md)
- Add `EtsyListingService` section
- Add 4 new endpoint entries to the `routers/etsy.py` section

#### [MODIFY] [doc/MASTER_MAP.md](file:///d:/Janesh/ETSY/ETSY-pipeline/doc/MASTER_MAP.md)
- Add `services/etsy_listing_service.py`
- Add `shops/[shop_id]/publish/page.tsx`
- Add `shops/callback/page.tsx`

---

## Full File Change List

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

1. **Schemas** — `craftdesk_api/schemas/etsy.py` (no dependencies, unblocks everything)
2. **EtsyListingService** — `craftdesk_api/services/etsy_listing_service.py`
3. **Router** — `craftdesk_api/routers/etsy.py` — 4 new endpoints
4. **Frontend: Shops page** — real OAuth redirect + clickable cards
5. **Frontend: Callback page** — OAuth code exchange
6. **Frontend: Publish page** — 3-mode dashboard
7. **Docs** — `DETAILED.md`, `MASTER_MAP.md`
8. **Tests + Lint** — `pytest craftdesk_api/tests/test_etsy.py`, `ruff check . --fix`

---

## Risks & Edge Cases

| Risk | Mitigation |
|------|-----------|
| GCS unavailable locally | `is_gcp_available()` guard — `gcs_available: false` in response; UI shows clear notice |
| Raw GCS metadata contains vague template text | Always pipe through `MetadataWorker._parse_and_validate_response()` — same regex cleaners as pipeline |
| Etsy PDF digital file upload API | New endpoint `/listings/{id}/files` — non-fatal on failure (logs warning, `pdf_uploaded: false` in response) |
| Large file uploads (>10MB per mockup) | FastAPI `UploadFile` cap at 50MB total; UI shows file count/size warnings |
| Option 3 Gemini requires GCP_PROJECT_ID | Graceful fallback: return `{ title: theme_hint, description: "", tags: [] }` with a UI warning if unconfigured |
| OAuth callback state CSRF | `state` param stored in `sessionStorage` and verified on callback (matches existing PKCE flow pattern) |
| Existing tests break | All 4 new endpoints are purely additive; no existing signatures modified |

---

## Verification Plan

### Automated Tests
```bash
pytest craftdesk_api/tests/test_etsy.py -v   # all existing tests pass
ruff check . --fix && ruff format .
```

### Manual Verification (in order)
1. `/shops` — "Connect Etsy Shop" button → browser redirects to Etsy OAuth page (not a setTimeout simulation)
2. Etsy redirects back to `/shops/callback` → loading spinner → success → `/shops` with new shop visible
3. Click a shop card → navigates to `/shops/<id>/publish`
4. Option 1 tab: if GCS available — folder list shows; if not — graceful notice
5. Option 2 tab: upload mockups + PDF + fill form → Publish → success panel with Etsy link
6. Option 3 tab: upload mockups → Generate → metadata auto-fills → edit → Publish → success panel
