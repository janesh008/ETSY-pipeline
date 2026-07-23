# Metadata Generation & CSV Consolidation Workers

Documentation for `MetadataWorker` and `CSVWorker` (Phase 8 of the Etsy pipeline).

---

## 1. MetadataWorker (`etsy_pipeline/workers/metadata_worker.py`)

### Responsibility
Generates SEO-optimized Etsy listing metadata (title, 8-section description, and 13 tags) using Gemini 2.5 Flash Vision.

### Input Artifacts
- Mockup PNGs from GCS: `Clipart/<date>/<theme_slug>/mockups/`
- Master prompt: `etsy_pipeline/resources/Deepseek_etsy_listing_generator_prompt.txt`

### Validation Rules
- **Title:** ≤140 characters, invalid characters stripped via regex, single occurrence check for `%`, `:`, `&`, `+`.
- **Description:** UTF-8 clean, HTML tags stripped, ≤102,400 characters.
- **Tags:** Exactly 13 tags, each ≤20 characters, multi-word phrases.

### Output Artifacts
- `Job` state fields: `job.etsy_title`, `job.etsy_description`, `job.etsy_tags`
- GCS raw Gemini response: `Clipart/<date>/<theme_slug>/metadata/raw_response.txt`

---

## 2. CSVWorker (`etsy_pipeline/workers/csv_worker.py`)

### Responsibility
Aggregates generated listing metadata into a consolidated per-date CSV file for human review and bulk management. Syncs the updated CSV to **both GCS and Google Drive** for dual-storage redundancy.

### File Locations
- Local path: `output/<date>/all_listings.csv`
- GCS path: `csv/<date>/all_listings.csv`
- Google Drive path: `Clipart/csv/<date>/all_listings.csv`

### Row Schema
```csv
JOB_ID,THEME,TITLE,DESCRIPTION,TAGS,PRICE,QUANTITY,WHO_MADE,WHEN_MADE,TAXONOMY_ID,TYPE,IS_DIGITAL,MATERIALS,SECTION_ID,MOCKUP_GCS_PREFIX,PDF_DRIVE_LINK,LISTING_ID,LISTING_URL
```
