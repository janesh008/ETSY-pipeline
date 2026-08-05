# Plan: Fix Etsy Publish Payload Keys and Error Handling

**Date:** 2026-08-05
**Status:** done
**Related:** [page.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/shops/%5Bslug%5D/publish/page.tsx)

---

## Problem
When publishing an Etsy listing from a GCS folder, the frontend sends payload keys `title_override`, `description_override`, and `tags_override` instead of `title`, `description`, and `tags` expected by the backend `GcsListingRequest` schema. This causes the custom values to be ignored. Furthermore, if a backend error occurs and returns a plain text response (e.g. "Internal Server Error"), the frontend crash due to `res.json()` failure masks the actual error with a cryptic JSON parsing message.

---

## Approach
1. Align the payload keys in the frontend's API request to match the backend expectations.
2. Improve error handling in the frontend fetch block by checking response OK/status, verifying JSON content-type if needed, or catching the parse error to fall back to a status message.

**Alternatives considered:**
- Adding aliases/fields on the backend schema to support `title_override`, etc. — rejected because it adds unnecessary complexity to the API schema when aligning keys is cleaner.

---

## Scope

**Files/modules touched:**
- `craftdesk_web/src/app/shops/[slug]/publish/page.tsx` — Update payload keys in `handlePublishGcs` and improve response error handling.

**Out of scope:**
- Modifying backend schemas or logic.

---

## Risks & edge cases
- Response has a non-JSON body — mitigated by catching parser failure or checking headers, then falling back to `res.statusText` or a HTTP status message.

---

## Steps
1. Modify `craftdesk_web/src/app/shops/[slug]/publish/page.tsx` fetch call.
2. Verify frontend lint/type check.
3. Test locally.

---

## Rollback
- Revert changes in `craftdesk_web/src/app/shops/[slug]/publish/page.tsx` via Git.
