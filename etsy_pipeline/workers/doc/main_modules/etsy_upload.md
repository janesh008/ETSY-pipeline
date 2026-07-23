# Etsy Listing Upload Worker & OAuth Tooling

Documentation for `EtsyWorker` and CLI scripts (Phase 9 of the Etsy pipeline).

---

## 1. EtsyWorker (`etsy_pipeline/workers/etsy_worker.py`)

### Responsibility
Communicates with Etsy Open API v3 to create draft listings, upload mockup images (Hero.png cover photo first), publish listings live, and save listing URLs.

### Workflow
1. Refresh OAuth 2.0 access token if expired.
2. Fetch taxonomy ID for "Clip Art" (`110`).
3. `POST /v3/application/shops/{shop_id}/listings` — create draft listing.
4. Sort mockup images (`Hero.png` cover image first) and upload up to 10 images.
5. `PATCH /v3/application/shops/{shop_id}/listings/{listing_id}` — update state to `active`.
6. Save `job.etsy_listing_id` and `job.etsy_listing_url`.

---

## 2. CLI Tooling

### `scripts/etsy_oauth.py`
Interactive OAuth 2.0 PKCE helper to generate initial `ETSY_ACCESS_TOKEN` and `ETSY_REFRESH_TOKEN`. Saves credentials directly to `.env`.

### `scripts/run_metadata_worker.py`
Daemon runner for automated Shot 1 execution (Metadata Generation + CSV Consolidation).

### `scripts/run_etsy_upload.py`
CLI script for manual Shot 2 execution (Human-triggered upload after reviewing CSV).
Usage:
```bash
python scripts/run_etsy_upload.py --job-id <job_id>
# or
python scripts/run_etsy_upload.py --theme "Wonder Woman"
```
