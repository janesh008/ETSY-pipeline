# Plan: Fix missing return paths in EtsyOAuthService.get_shop_details

**Date:** 2026-08-01
**Status:** approved
**Related:** `craftdesk_api/services/etsy_oauth.py`

---

## Problem
`EtsyOAuthService.get_shop_details` in `craftdesk_api/services/etsy_oauth.py` is annotated to return `dict[str, Any]`, but missing return/raise statements when HTTP request fails or when exceptions occur cause execution to implicitly return `None`.

---

## Approach
- Add explicit error raising (`raise RuntimeError(...)`) when `me_resp.status_code != 200`.
- Re-raise caught exceptions (`raise`) in the `except Exception as exc:` block.
- This ensures all execution paths either return a `dict[str, Any]` or raise an exception, preventing implicit `None` returns and satisfying the return type annotation.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/services/etsy_oauth.py` — Add explicit `raise` statements on error/exception paths in `get_shop_details`.

**Out of scope:**
- Modifying router error handling or changing OAuth token exchange methods.

---

## Risks & edge cases
- Caller code (`craftdesk_api/routers/etsy.py`) already wraps `get_shop_details` calls in a `try...except Exception` block, converting failures into standard `HTTPException(400)`. Explicitly raising an exception on HTTP error matches existing error handling behavior cleanly.

---

## Steps
1. Update `craftdesk_api/services/etsy_oauth.py` `get_shop_details` method.
2. Run pytest suite on `craftdesk_api/tests/test_etsy.py` to verify tests pass cleanly.

---

## Rollback
Revert changes to `craftdesk_api/services/etsy_oauth.py`.
