# Plan: Add Debug Logging and Settings Sourcing to EtsyOAuthService.get_shop_details

**Date:** 2026-08-01
**Status:** approved
**Related:** `craftdesk_api/services/etsy_oauth.py`

---

## Problem
In `EtsyOAuthService.get_shop_details`, `ETSY_SHARED_SECRET` was relying on `os.getenv("ETSY_SHARED_SECRET")` evaluated at import time, which returned `""` when `uvicorn` ran without explicit shell environment variable exports. This caused the `x-api-key` header to miss the shared secret, resulting in HTTP 403 errors from Etsy API v3. Furthermore, stage-by-stage debug logs were needed to identify exact failure points during OAuth connection.

---

## Approach
1. Import `settings` from `craftdesk_api.core.config` so `etsy_keystring` and `etsy_shared_secret` are reliably retrieved via Pydantic `.env` configuration or defaults.
2. Add step-by-step debug logging (`logger.info`, `logger.error`, `logger.warning`) inside `get_shop_details` for:
   - Header credentials (masked for security).
   - Stage 1 `/users/me` request, HTTP status, and response keys/errors.
   - Stage 2 `/users/{user_id}/shops` request, status, and shop extraction.
   - Specific exception handlers for `httpx.HTTPStatusError`, `httpx.RequestError`, and generic `Exception`.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/etsy_oauth.py` — Update `get_shop_details` with settings sourcing and stage logging.
- `craftdesk_api/tests/test_etsy.py` — Verify unit tests continue to pass.

**Out of scope:**
- Router or database changes.

---

## Risks & edge cases
- Mask sensitive credentials in log outputs to prevent plain-text secret leaking in server logs.

---

## Steps
1. Save this plan file.
2. Update `craftdesk_api/services/etsy_oauth.py`.
3. Run `ruff` and `pytest`.
4. Update repository graph.

---

## Rollback
Revert `craftdesk_api/services/etsy_oauth.py`.
