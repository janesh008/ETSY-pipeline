# Plan: Fix x-api-key Header Format in EtsyOAuthService.get_shop_details

**Date:** 2026-08-01
**Status:** approved
**Related:** `craftdesk_api/services/etsy_oauth.py`

---

## Problem
Etsy Open API v3 returns HTTP 403 `{"error":"Shared secret is required in x-api-key header."}` during shop connection because `get_shop_details` in `craftdesk_api/services/etsy_oauth.py` sends only the keystring in `x-api-key`, omitting the shared secret (`<keystring>:<shared_secret>`).

---

## Approach
- Add `ETSY_SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET", "")` to `craftdesk_api/services/etsy_oauth.py`.
- Update `get_shop_details` to accept optional `shared_secret: str | None = None` (defaulting to `ETSY_SHARED_SECRET`).
- Format `x-api-key` header as `f"{client_id}:{secret}"` when `secret` is present.
- Update tests in `craftdesk_api/tests/test_etsy.py` to verify the header format.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/etsy_oauth.py` — Update `x-api-key` header formatting.
- `craftdesk_api/tests/test_etsy.py` — Add/update test to check `x-api-key` header contains shared secret.

**Out of scope:**
- Token exchange endpoints (`exchange_code_for_tokens` uses OAuth body parameters `client_id`, not `x-api-key`).

---

## Risks & edge cases
- If `shared_secret` is empty, fallback cleanly to `keystring` only without appending a colon.

---

## Steps
1. Save this plan file.
2. Update `craftdesk_api/services/etsy_oauth.py`.
3. Update `craftdesk_api/tests/test_etsy.py`.
4. Run `ruff` and `pytest` to verify.

---

## Rollback
Revert `craftdesk_api/services/etsy_oauth.py` and `craftdesk_api/tests/test_etsy.py`.
