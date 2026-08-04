# Plan: Async Pipeline Job Execution & Etsy Publishing Redesign

**Date:** 2026-08-04
**Status:** done
**Related:** [pipeline_runner.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/pipeline_runner.py), [etsy_listing_service.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_listing_service.py)

---

## Problem
The pipeline job execution system suffered from critical lifecycle bugs: ghost jobs auto-resumed on VM boot, 4s aggressive polling never stopped, clear/cancel did not stick, and jobs got stuck between stages. Additionally, users needed per-stage retry on any stage, a notification bell instead of a floating popup, drag-resizable split panes, and robust checks for GCS mockups/PDF completion. Finally, Etsy listing uploads suffered from concurrency rate-limits (causing only 2-3 images to upload) and mismatches in the auto-renewal configuration payload.

---

## Design Decisions
1. **Manual Resume**: Do not auto-resume running/queued jobs on VM startup; mark them as `interrupted` and require manual resume.
2. **Startup Cache Pruning**: Delete terminal jobs (`completed` or `failed`) from the JSON cache on startup to keep operations fast.
3. **Task Concurrency Guard**: Prevent duplicate concurrent pipeline loops on the same job ID by tracking active tasks and cancelling older ones on stop/retry.
4. **Sequential Image Uploading**: Upload listing mockup images sequentially with a 1.0-second delay between requests to prevent rate-limiting lockouts on Etsy.
5. **Auto-Renewal Mapping**: Map the UI `renewal_option` parameter to the official Etsy API v3 boolean parameter `should_auto_renew`.

---

## Scope

### Files/modules touched:
- [pipeline_runner.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/pipeline_runner.py) — Implemented orphan sanitization, cache pruning, task concurrency cancellation, GCS mockup/PDF completion verification, and sequential mockup uploading with rate-limit sleep guards.
- [routers/pipeline.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/pipeline.py) — Created manual resume endpoint, updated retry endpoint to trigger cascading pipeline execution, and added in-memory cache clearing.
- [routers/review.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/routers/review.py) — Implemented local file proxy media endpoint and mapped metadata `renewal_option` to the Etsy publisher.
- [etsy_listing_service.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_listing_service.py) — Mapped `renewal_option` to `should_auto_renew` in draft payload, and removed hardcoded localhost prefix from media lister.
- [etsy_publisher.py](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/etsy_publisher.py) — Updated `create_draft_listing` payload to include `should_auto_renew`.
- [models/job.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/models/job.py) — Extracted case-sensitive theme folder slug from prompt filepath to ensure exact GCS directory matching.
- [PipelineContext.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/context/PipelineContext.tsx) — Added adaptive polling (only syncs when a job is active) and clear/cancel immunity timers.
- [PipelineNotificationBell.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/components/pipeline/PipelineNotificationBell.tsx) — Pulsing notification bell with progress bars and controls.
- [page.tsx (Pipeline Page)](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/pipeline/page.tsx) — Draggable split pane, stage retry buttons, history log, and controls layout.
- [publish/page.tsx (Publish Page)](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/app/shops/%5Bslug%5D/publish/page.tsx) — Support relative media proxy URLs starting with `/` inside mockups grid and lightbox.

---

## Risks & edge cases
- **Etsy Concurrency Locks**: Mitigated by sequential listing image uploads + 1.0s delay.
- **Unrecognized Fields in Etsy API**: Mapped `renewal_option` to the official `should_auto_renew` boolean field. AI disclosure is documented as a manual UI compliance requirement since the v3 API has no exposed toggle.

---

## Steps & Rollback
- Revert changes via Git on the 10 listed files to roll back.
