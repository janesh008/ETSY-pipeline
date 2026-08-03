# Implementation Plan — Fix Etsy API Listing Image Upload 409 Conflict & Activation 404 Error

Date: 2026-08-03  
Branch: `feat/batch-pipeline-background-widget`  

---

## Problem Statement

Based on the backend terminal diagnostic logs:

1. **HTTP 409 Conflict on Image Upload**:
   `[etsy_listing_service] Image upload failed for 'Main_character_4.png' (HTTP 409): {"error":"The Listing with listing_id 4548870341 is being edited by another process. Please try again in a few moments."}`
   - **Root Cause**: `_upload_mockup_images()` used `ThreadPoolExecutor(max_workers=5)` to send 5 parallel HTTP POST requests to Etsy for the same listing ID. Etsy's API locks a listing during image attachment and rejects concurrent edit requests with `HTTP 409`.

2. **HTTP 404 Resource Not Found on Activation**:
   `[etsy_listing_service] [Stage 4 ERROR] Failed to activate listing_id=4548870341 (HTTP 404): {"error": "Resource not found"}`
   - **Root Cause**: `_publish_listing()` called `requests.put()`. In Etsy API v3, `PUT` is full resource replacement (requiring all listing parameters). Sending a partial JSON `{ "state": "active" }` via `PUT` returns HTTP 404. `PATCH` must be used for partial state updates.

---

## Proposed Changes

### [CraftDesk API Component]

#### [MODIFY] [etsy_listing_service.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_listing_service.py)
1. **Sequential Image Uploads (`_upload_mockup_images`)**:
   - Replace `ThreadPoolExecutor` with sequential `for` loop uploading mockup images one by one with a small 0.3s pause between uploads.
2. **PATCH for Listing State Activation (`_publish_listing`)**:
   - Change `requests.put()` to `requests.patch()` for `state: "active"` update, matching `EtsyWorker._publish_listing()`.

---

## Verification Plan

### Automated Tests
- Run `python -m pytest craftdesk_api/tests/test_etsy.py`
