# Metadata Generation + Etsy Upload (Phases 8 & 9) — Implementation Plan

> Date: 2026-07-22  
> Status: **Completed**

---

## Overview

Implemented two-shot architecture for Etsy listing metadata generation, CSV consolidation, and live Etsy Open API v3 listing uploads:

1. **Shot 1 (Automated Daemon):** `MetadataWorker` uses Gemini 2.5 Flash Vision fed with mockup PNGs from GCS and `Deepseek_etsy_listing_generator_prompt.txt` to generate titles (≤140 chars), descriptions, and 13 tags (≤20 chars each). `CSVWorker` appends listing data to `output/<date>/all_listings.csv` and syncs with GCS.
2. **Shot 2 (Human Triggered CLI):** `run_etsy_upload.py` runs `EtsyWorker` to create draft listings via Etsy v3 API, upload mockup images with `Hero.png` first, activate listings, and record listing URLs.

---

## Created and Modified Files

- **`etsy_pipeline/models/job.py`**: Added `etsy_title`, `etsy_description`, `etsy_tags`, `listing_price_usd`, `listing_quantity`, `etsy_listing_id`, `etsy_listing_url` fields.
- **`etsy_pipeline/config/settings.py` & `.env.example`**: Added Etsy OAuth credentials and pricing defaults.
- **`etsy_pipeline/workers/metadata_worker_config.py`**: Created validation constraints and master prompt path constants.
- **`etsy_pipeline/workers/metadata_worker.py`**: Gemini 2.5 Flash Vision worker with strict title/tag/description validation.
- **`etsy_pipeline/workers/csv_worker.py`**: Consolidated per-date CSV file management and GCS sync.
- **`scripts/run_metadata_worker.py`**: Daemon CLI runner for Metadata + CSV stages.
- **`scripts/etsy_oauth.py`**: Interactive OAuth 2.0 PKCE token generator script.
- **`etsy_pipeline/workers/etsy_worker.py`**: Etsy Open API v3 listing creation and image upload worker.
- **`scripts/run_etsy_upload.py`**: Manual CLI upload trigger.
- **`etsy_pipeline/pipeline/orchestrator.py`**: Wired new worker stages into the pipeline.
- **`tests/test_metadata_worker.py` & `tests/test_csv_worker.py`**: Unit tests for validation, CSV formatting, and Hero-first sorting.
- **`etsy_pipeline/workers/doc/metadata.md` & `etsy_upload.md`**: Worker documentation.
