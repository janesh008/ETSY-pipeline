# Plan: Wire Stage 4 (Mockup Creation) & Stage 5 (Clickable PDF Wrap) into API & UI

**Date:** 2026-07-30  
**Status:** approved  
**Related:** [`craftdesk_api/doc/PIPELINE_ARCHITECTURE.md`](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/doc/PIPELINE_ARCHITECTURE.md)

---

## Problem
`MockupWorker` (Stage 4 & Stage 5) generates mockup images, a ReportLab A4 PDF wrapper, and a public Google Drive share link, but `craftdesk_api` hardcoded a fake demo URL (`demo-pdf-...`) in the review endpoint, and `craftdesk_web` lacked visual mockup previews in Stage 4 and download action buttons in Stage 5.

---

## Approach
1. **`craftdesk_api` Integration**:
   - Update `PipelineJobResponse` schema with `mockups: list[str]`, `hero_image_url: Optional[str]`, `pdf_drive_link: Optional[str]`, and `pdf_local_path: Optional[str]`.
   - Update `PipelineRunnerService` to populate `pdf_drive_link`, `pdf_local_path`, `mockups`, and `hero_image_url` into `job_data` when Stage 4/5 completes.
   - Add `GET /api/v1/pipeline/jobs/{job_id}/pdf` endpoint returning `FileResponse` for the generated PDF.
   - Update `GET /api/v1/review/{job_id}` router to use `job.get("pdf_drive_link")` and `job.get("mockups")`.

2. **`craftdesk_web` Integration**:
   - **Stage 4 Card (`mockup_creation`)**: Render a 4-item image thumbnail preview grid of the generated product mockups.
   - **Stage 5 Card (`pdf_generation`)**: Render interactive **📄 Open Google Drive Clipart Bundle** (`target="_blank"`) and **💾 Download PDF Wrapper** action buttons.
   - **Review Page (`/review/[job_id]`)**: Connect PDF download link and mockup gallery to real API data.

---

## Scope

**Files/modules touched:**
- `craftdesk_api/schemas/pipeline.py` — Add PDF and mockup fields to schema.
- `craftdesk_api/services/pipeline_runner.py` — Populate PDF and mockup fields in `job_data`.
- `craftdesk_api/routers/pipeline.py` — Add `GET /api/v1/pipeline/jobs/{job_id}/pdf` endpoint.
- `craftdesk_api/routers/review.py` — Return real `pdf_drive_link` and `mockups`.
- `craftdesk_web/src/app/pipeline/page.tsx` — Add Mockup gallery grid & PDF action buttons.
- `craftdesk_web/src/app/review/[job_id]/page.tsx` — Connect real PDF download link.

---

## Steps
1. Update `craftdesk_api` schemas, pipeline runner service, and routers.
2. Update `craftdesk_web` `/pipeline` and `/review/[job_id]` pages.
3. Run `pytest craftdesk_api/tests/test_pipeline.py` and `pytest craftdesk_api/tests/test_review.py`.
4. Run `ruff check`.
5. Rebuild repo graph (`python scripts/build_graph.py`).
