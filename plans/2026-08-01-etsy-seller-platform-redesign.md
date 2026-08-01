# Plan: Scalable Etsy Seller Platform & Workspace Navigation Redesign

**Date:** 2026-08-01
**Status:** approved
**Related:** `craftdesk_api/routers/etsy.py`, `craftdesk_api/models/etsy_shop.py`, `craftdesk_web/src/app/shops`

---

## Problem
1. **Route Structure:** URLs use database UUIDs (`/shops/4e2f10e9.../publish`) rather than user-friendly Etsy shop names/slugs.
2. **Shop Page Architecture:** `/shops/[shop_id]/publish` is a monolithic single page instead of a scalable multi-module workspace.
3. **GCS Theme Selector:** Single-select dropdown cannot scale to 1,000+ theme folders; lacks multi-selection, virtualized rendering, search, and batch actions.

---

## Approach

### 1. Database & Backend Slug Resolution
- Add indexed `slug` column to `EtsyShop` ORM model (`craftdesk_api/models/etsy_shop.py`).
- Implement `slugify_shop_name()` in `craftdesk_api/utils/slug.py`.
- Add `get_shop_by_identifier()` in `craftdesk_api/routers/etsy.py` to seamlessly resolve `slug`, `shop_name`, `shop_id` (numeric Etsy ID), or `id` (UUID), guaranteeing 100% backward compatibility.
- Update `EtsyShopResponse` schema to include `slug`.

### 2. Frontend Next.js App Router Workspace
- Create `/shops/[slug]/layout.tsx` for the Workspace Layout Shell with persistent Header, Store Switcher dropdown, status badge, and sub-module navigation bar.
- Create `/shops/[slug]/page.tsx` for Overview dashboard (metrics, stats, quick actions).
- Update `/shops/[slug]/publish/page.tsx` as the Publish Listings module within the workspace.
- Create extension tabs (`/shops/[slug]/optimizer`, `/shops/[slug]/listings`, `/shops/[slug]/settings`) to demonstrate workspace scalability.

### 3. Enterprise GCS Clipart Theme Selector
- Create `EnterpriseGcsThemeSelector.tsx`:
  - Windowed/lazy virtualized rendering for 1,000+ folders.
  - Multi-select, Select All, Clear All, search box, folder badges.
  - Floating batch publish action bar.
  - Full keyboard accessibility.

---

## Scope

**Files touched/created:**
- `craftdesk_api/models/etsy_shop.py`
- `craftdesk_api/utils/slug.py`
- `craftdesk_api/routers/etsy.py`
- `craftdesk_api/schemas/etsy.py`
- `craftdesk_web/src/lib/slug.ts`
- `craftdesk_web/src/app/shops/page.tsx`
- `craftdesk_web/src/app/shops/[slug]/layout.tsx`
- `craftdesk_web/src/app/shops/[slug]/page.tsx`
- `craftdesk_web/src/app/shops/[slug]/publish/page.tsx`
- `craftdesk_web/src/app/shops/[slug]/optimizer/page.tsx`
- `craftdesk_web/src/app/shops/[slug]/listings/page.tsx`
- `craftdesk_web/src/app/shops/[slug]/settings/page.tsx`
- `craftdesk_web/src/components/gcs/EnterpriseGcsThemeSelector.tsx`

---

## Execution Steps
1. **Backend Implementation:**
   - Create `craftdesk_api/utils/slug.py`.
   - Update `EtsyShop` model in `craftdesk_api/models/etsy_shop.py`.
   - Update schemas in `craftdesk_api/schemas/etsy.py`.
   - Update endpoints in `craftdesk_api/routers/etsy.py`.
2. **Frontend Implementation:**
   - Create `craftdesk_web/src/lib/slug.ts`.
   - Create `EnterpriseGcsThemeSelector.tsx`.
   - Create `/shops/[slug]/layout.tsx`, `/shops/[slug]/page.tsx`, `/shops/[slug]/publish/page.tsx`, and extension tabs.
   - Update `/shops/page.tsx`.
3. **Verification:**
   - Run `pytest craftdesk_api/tests/test_etsy.py`.
   - Run `ruff check`.
   - Rebuild graph with `build_graph.py`.
