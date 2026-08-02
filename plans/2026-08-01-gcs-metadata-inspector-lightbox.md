# Implementation Plan — GCS Theme Metadata Inspector & Mockup Lightbox Modal

## Problem Statement
When users select GCS clipart theme folders in the right-side selector, the center panel currently displays empty fallback inputs. Users need live inspection and editing of GCS `listing.json` metadata (Title, Description, Tags, Price, Stock, Who Made, Is Digital) for both single and stacked multi-theme selections, as well as a smooth lightbox modal for inspecting mockup images.

---

## Proposed Approach

1. **Backend Endpoint (`craftdesk_api/routers/etsy.py` & `etsy_listing_service.py`):**
   - Implement `GET /api/v1/etsy/gcs-folder-details?gcs_prefix=...` endpoint.
   - Parses `listing.json` and lists mockup image URLs in `Clipart/{date}/{theme}/mockups/`.

2. **Center Panel Multi-Theme Stack & Form (`publish/page.tsx`):**
   - Maintain a dictionary of theme metadata indexed by `gcs_prefix`.
   - Single Selection: Auto-populate Title, Description, Tags, Price, Quantity, `who_made` ("i_did"), `is_digital` (boolean checkbox).
   - Multi-Selection: Render a **Theme Selector Tab Bar** at the top of the form allowing seamless tab switching between selected themes.

3. **Mockup Thumbnail Strip & Smooth Lightbox Modal:**
   - Display a row of small mockup thumbnail icons in the center panel.
   - Clicking any thumbnail opens a full-screen **Mockup Gallery Lightbox Modal** with bottom thumbnail filmstrip, prev/next buttons, and keyboard arrow key navigation.

---

## Files / Modules Touched
- [MODIFY] [`craftdesk_api/schemas/etsy.py`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/schemas/etsy.py)
- [MODIFY] [`craftdesk_api/services/etsy_listing_service.py`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_listing_service.py)
- [MODIFY] [`craftdesk_api/routers/etsy.py`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/etsy.py)
- [MODIFY] [`craftdesk_web/src/app/shops/[slug]/publish/page.tsx`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/shops/[slug]/publish/page.tsx)

---

## Ordered Implementation Steps

### Step 1: Add GCS Folder Details Endpoint (`craftdesk_api`)
- Add `GcsFolderDetailsResponse` Pydantic schema in `schemas/etsy.py`.
- Add `get_gcs_folder_details()` method in `etsy_listing_service.py` to return `listing.json` and list mockup file paths/URIs.
- Expose `GET /api/v1/etsy/gcs-folder-details` in `routers/etsy.py`.

### Step 2: Implement Lightbox Modal & Metadata Stack (`publish/page.tsx`)
- Add state for loaded theme metadata records, active selected theme tab, and lightbox modal open index.
- Automatically fetch folder details when `selectedFolderPrefixes` changes.
- Build editable form fields (Title, Description, Tags, Price, Quantity, `who_made`, `is_digital`).
- Build Image Lightbox Modal with smooth sliding navigation.

### Step 3: Verification & Build
- Run `pytest craftdesk_api/tests/test_etsy.py`.
- Run `npm run build` in `craftdesk_web`.
