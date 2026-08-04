# Implementation Plan — Async Pipeline Job Execution Redesign

**Date:** 2026-08-04  
**Status:** approved  
**Branch:** `feat/pipeline-async-redesign`

---

## Problem Statement

The pipeline job execution system has critical lifecycle bugs: ghost jobs auto-resume on VM boot, 4s aggressive polling never stops, clear/cancel don't stick, and jobs get stuck between stages. Additionally, users need per-stage retry on any stage (not just failed), a notification bell instead of a floating popup, and resizable split panes.

---

## Design Decisions

| Decision | Answer |
|----------|--------|
| Auto-resume interrupted jobs? | No — require manual Resume |
| Job retention in cache? | Purge completed/failed on startup |
| Concurrent or sequential? | Sequential |
| Redis needed? | No — in-memory + JSON cache sufficient at current scale |

---

## Changes (8 files)

1. `pipeline_runner.py` — Orphan detection, cache pruning, `resume_job()`, debug logging
2. `schemas/pipeline.py` — `"interrupted"` status
3. `routers/pipeline.py` — Resume endpoint, any-stage retry, error detail responses
4. `PipelineContext.tsx` — Hardened sync, adaptive polling, cancel/clear immunity
5. `PipelineNotificationBell.tsx` — Header notification bell (NEW)
6. `layout.tsx` — Remove floating widget
7. `pipeline/page.tsx` — Resizable split, per-stage retry, interrupted banner, history
8. `FloatingPipelineWidget.tsx` — DELETE

---

## Rollback

Git revert changes to the 8 listed files.
