# Implementation Plan — Multi-Prompt Batch Pipeline & Global Background Execution Widget

Date: 2026-08-02  
Branch: `feat/batch-pipeline-background-widget`  

---

## Problem Statement

1. **Unnecessary Idle Polling**: `GET /api/v1/pipeline/comfyui/status` polls continuously every 8s (or 2–5s) even when no pipeline is running, wasting network bandwidth.
2. **Single-Prompt Limitation**: The current pipeline UI only allows selecting and running 1 prompt file at a time.
3. **Navigational Interruptions**: If the user leaves `/pipeline` to browse `/shops`, `/dashboard`, or `/settings`, the UI state is lost or appears interrupted.
4. **Basic Selector**: `/pipeline` uses a plain dropdown instead of the rich, enterprise GCS folder selector with search, date filters, and feature badges (`EnterpriseGcsThemeSelector`) present in `shop/<slug>/publish`.

---

## User Review Required

> [!IMPORTANT]
> - **Global Background Execution**: We will wrap the app in a `<PipelineProvider>` (React Context) so pipeline job progress survives page navigation.
> - **Floating Mini Widget**: A floating progress banner will appear in the bottom-right corner (`bottom-6 right-6 z-50`) whenever a batch or job is running. Clicking it anywhere will navigate directly back to `/pipeline`.
> - **Sequential Batch Processing**: When multiple prompt folders are selected, the pipeline engine processes them sequentially (Theme 1 → Theme 2 → Theme N), displaying per-theme progress bars and batch completion stats.

---

## Proposed Changes

### 1. ComfyUI Polling Optimization
- Modify `craftdesk_web/src/app/pipeline/page.tsx`:
  - Eliminate aggressive continuous interval polling when idle or once ComfyUI is confirmed `running`.
  - Only poll on mount or when an active job enters image generation.

### 2. Universal Enterprise GCS Folder Selector
- Modify `craftdesk_web/src/components/gcs/EnterpriseGcsThemeSelector.tsx`:
  - Support both `onBatchPublish` and `onBatchPipelineRun` callbacks.
  - Display GCS theme folders with multi-select checkboxes, search bar, date filter calendar, and feature badges (`Mockups`, `PDF`, `JSON`, `Prompts`).

### 3. Global Pipeline Context (`PipelineContext`)
- Create `craftdesk_web/src/context/PipelineContext.tsx`:
  - State: `batchQueue` (list of selected themes), `currentJobIndex`, `activeJob` (stage name, stage progress %, total steps, elapsed time, status).
  - Methods: `startBatchRun(folders)`, `pauseBatch()`, `cancelBatch()`.
  - Wraps `children` in `craftdesk_web/src/app/layout.tsx`.

### 4. Floating Background Progress Mini-Widget
- Create `craftdesk_web/src/components/pipeline/FloatingPipelineWidget.tsx`:
  - Fixed at `bottom-6 right-6 z-50`.
  - Displays: Batch count (e.g. `Theme 2 of 5`), active theme name, current stage (e.g. `Image Generation (4/22)`), animated progress ring/bar, and pause/cancel controls.
  - Clicking the widget invokes `router.push('/pipeline')`.

### 5. Multi-Prompt Batch Execution UI on `/pipeline`
- Update `craftdesk_web/src/app/pipeline/page.tsx`:
  - Show batch progress overview (overall batch bar + queue list of themes with individual status tags: `Queued`, `Processing`, `Completed`, `Failed`).

---

## Verification Plan

### Automated Verification
- `npx tsc --noEmit` in `craftdesk_web/`
- `npm run build` in `craftdesk_web/`

### Manual Verification
- Select 3 prompt folders in GCS Theme Selector on `/pipeline`.
- Click "Batch Run Pipeline (3 Themes)".
- Observe sequential execution and live progress updates.
- Navigate to `/dashboard` or `/shops` — verify the floating mini-widget appears in the bottom right with live progress.
- Click the mini-widget — verify it smoothly navigates back to `/pipeline`.
- Check DevTools Network tab — verify `comfyui/status` is not continuously polled when idle.
