# Plan: Replace Per-Date CSV with Per-Theme `listing.json`

**Date:** 2026-07-31
**Status:** approved
**Scope:** `etsy_pipeline` package + scripts + tests (no `craftdesk_api` changes)

---

## Problem Statement

`CSVWorker` writes a **shared per-date `all_listings.csv`** that accumulates rows from
all themes run on the same day. This design has three compounding problems:

1. **Write-race risk:** Two concurrent jobs on the same day both read-modify-write the
   same `all_listings.csv`, which can corrupt the file.
2. **CSV format limitations:** Multi-line descriptions require `\n` escaping hacks;
   tags become pipe-delimited strings instead of native arrays.
3. **Discovery gap:** The CraftDesk Etsy Connector (Shop Publish Dashboard, Option 1)
   needs to read metadata per-theme to pre-fill the listing form. A shared date-level
   CSV is the wrong granularity.

Additionally, `CSVWorker` is **never called** by `craftdesk_api/services/pipeline_runner.py`
(the web-tier pipeline runner). It is only called from:
- `etsy_pipeline/pipeline/orchestrator.py`
- `scripts/run_metadata_worker.py`
- `scripts/run_etsy_upload.py`

---

## Proposed Approach

Replace `CSVWorker` with `ListingRecordWorker`, which writes one `listing.json` per theme:

```
GCS / local output:
  Clipart/
    2026-07-22/
      Wonder_Woman_Birthday/
        metadata/
          raw_response.txt        <- existing (unchanged)
          listing.json            <- NEW: replaces the CSV row
```

`EtsyWorker` writes `etsy_listing_id` and `etsy_listing_url` back into this same file
after upload, replacing the old "re-read CSV, update row, re-upload" pattern.

---

## Full Blast Radius

| File | Current CSV usage | Action |
|------|-------------------|--------|
| `etsy_pipeline/workers/csv_worker.py` | Core implementation | REPLACE with `listing_record_worker.py` |
| `etsy_pipeline/models/job.py` | `csv_path` field | RENAME to `listing_record_path`; stage key `csv_generation` -> `listing_record` |
| `etsy_pipeline/pipeline/orchestrator.py` | Imports + wires CSVWorker | UPDATE import + stage name |
| `scripts/run_metadata_worker.py` | Imports + calls csv_worker.run() | UPDATE to listing_record_worker.run() |
| `scripts/run_etsy_upload.py` | Imports + calls csv_worker.run() post-upload | REMOVE call (write-back moves into EtsyWorker) |
| `tests/test_csv_worker.py` | Tests CSV_HEADERS, _build_row_dict | REPLACE with test_listing_record_worker.py |
| `etsy_pipeline/utils/exceptions.py` | CSVGenerationError | ADD ListingRecordError; keep old |
| `etsy_pipeline/workers/etsy_worker.py` | No CSV usage today | ADD _update_listing_record() write-back |

**Not touched:** `craftdesk_api/` — pipeline runner there never called CSVWorker.

---

## New JSON Schema (`listing.json`)

```json
{
  "job_id": "abc123",
  "theme": "Wonder Woman Birthday",
  "theme_slug": "Wonder_Woman_Birthday",
  "date_folder": "2026-07-22",
  "generated_at": "2026-07-22T14:30:00Z",
  "etsy_title": "Wonder Woman Birthday Clipart PNG Bundle",
  "etsy_description": "High-res watercolor clipart...",
  "etsy_tags": ["wonder woman clipart", "birthday png"],
  "listing_price_usd": 18.0,
  "listing_quantity": 999,
  "who_made": "i_did",
  "when_made": "made_to_order",
  "taxonomy_id": 110,
  "type": "download",
  "is_digital": true,
  "materials": ["PNG", "Digital Download", "Transparent Background"],
  "mockup_gcs_prefix": "Clipart/2026-07-22/Wonder_Woman_Birthday/mockups/",
  "pdf_drive_link": "https://drive.google.com/...",
  "etsy_listing_id": "",
  "etsy_listing_url": ""
}
```

Written by `ListingRecordWorker`. Fields `etsy_listing_id` and `etsy_listing_url`
written back by `EtsyWorker._update_listing_record()` after successful upload.

---

## GCS Path Change

| Old | New |
|-----|-----|
| `csv/2026-07-22/all_listings.csv` (shared) | `Clipart/2026-07-22/Wonder_Woman/metadata/listing.json` (per-theme) |

Google Drive:

| Old | New |
|-----|-----|
| `Clipart/csv/2026-07-22/all_listings.csv` | `Clipart/raw_data/2026-07-22/Wonder_Woman_Birthday/metadata/listing.json` |

---

## Integration with Etsy Shop Connector

`EtsyListingService.load_and_clean_gcs_metadata()` will use a fast path:

1. Try: `Clipart/<date>/<slug>/metadata/listing.json` -> already clean native types, return directly
2. Fallback: `Clipart/<date>/<slug>/metadata/raw_response.txt` -> parse with MetadataWorker._parse_and_validate_response()

---

## Implementation Steps

1. Add `ListingRecordError` to `etsy_pipeline/utils/exceptions.py`
2. Rename field + stage key in `etsy_pipeline/models/job.py`
3. Create `etsy_pipeline/workers/listing_record_worker.py`
4. Add `_update_listing_record()` to `etsy_pipeline/workers/etsy_worker.py`
5. Update `etsy_pipeline/pipeline/orchestrator.py`
6. Update `scripts/run_metadata_worker.py`
7. Update `scripts/run_etsy_upload.py`
8. Delete `tests/test_csv_worker.py`; create `tests/test_listing_record_worker.py`
9. Update `etsy_pipeline/workers/doc/DETAILED.md`
10. Update `doc/MASTER_MAP.md`
11. Run: `ruff check . --fix && ruff format .`
12. Run: `pytest tests/test_listing_record_worker.py -v`
13. Run: `python scripts/build_graph.py`

---

## Risks & Rollback

| Risk | Mitigation |
|------|-----------|
| Existing `all_listings.csv` in GCS orphaned | Leave in place — historical records, no cleanup needed |
| `CSVGenerationError` caught externally | Kept in `exceptions.py`, not deleted |
| `listing.json` missing when EtsyWorker runs write-back | `_update_listing_record()` is non-fatal: logs warning only |
| Stage key rename breaks retry in orchestrator | Stage key `csv_generation` -> `listing_record`; no external API surfaces this key |
