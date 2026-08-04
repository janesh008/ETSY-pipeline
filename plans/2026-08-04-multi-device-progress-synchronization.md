# Plan: Multi-Device Progress Synchronization

**Date:** 2026-08-04
**Status:** approved
**Related:** [craftdesk_web/src/context/PipelineContext.tsx](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_web/src/context/PipelineContext.tsx)

---

## Problem
Currently, the React context `batchQueue` only tracks pipeline executions in memory for the active browser window/session. If the user closes the browser or logs in from another device (like mobile), they cannot see the active job's progress bar, even though the backend continues executing the pipeline to completion. Additionally, token expiration causes silent polling failures.

---

## Approach
1. Modify `craftdesk_web/src/context/PipelineContext.tsx` to add a backend sync mechanism:
   - Create a `syncJobsFromBackend` function that fetches `GET /api/v1/pipeline/jobs`.
   - Map backend jobs (`PipelineJobResponse`) to frontend `PipelineJobItem` structures.
   - Run this sync on mount to populate `batchQueue` with any recent/running jobs.
   - If a job is active/running, automatically start/resume the status polling loop.
   - Run periodic synchronization (e.g. every 5 seconds) to ensure desktop and mobile states stay perfectly aligned.
2. Gracefully handle access token expiration/failures (e.g., if API returns `401 Unauthorized` / invalid token, redirect to `/login` or prompt authentication).

---

## Scope

**Files/modules touched:**
- `craftdesk_web/src/context/PipelineContext.tsx` — Add mount-time job synchronization, auto-resume active job loops, periodic sync, and token expiration handling.

**Out of scope:**
- Backend API adjustments (endpoints are already ready).

---

## Steps
1. Implement job parsing and `syncJobsFromBackend` in `PipelineContext.tsx`.
2. Configure mount effect and periodic interval for status synchronization.
3. Validate and verify functionality by starting a job and testing cross-device progress.
4. Update walkthrough.md.

---

## Rollback
Git checkout `craftdesk_web/src/context/PipelineContext.tsx`.
