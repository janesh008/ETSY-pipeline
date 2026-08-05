# Plan: Developer Memory Abstraction Layer (TencentDB MemoryCore)

**Date:** 2026-08-05  
**Status:** Approved  
**Related:** [HIGH_LEVEL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/doc/HIGH_LEVEL.md)

---

## Problem
Currently, developer and AI coding context is lost between sessions. Antigravity requires a dynamic, persistent memory of past engineering decisions, architecture rules, bug fixes, and conventions without replacing static guardrails (`AGENTS.md`) or introducing brittle coupling to any specific memory vendor.

---

## Clarifying questions & answers
- **Q:** Should MemoryCore run as a separate HTTP service or be ported to Python?  
  **A:** MemoryCore runs as an isolated external HTTP service on `:8420` (Docker or Node.js). The Python core must NEVER directly import or depend on TencentDB internals.
- **Q:** How will the rest of the application access memory?  
  **A:** Through a provider-independent Python Memory Abstraction Layer (`BaseMemoryProvider`) exposing generic methods (`capture()`, `recall()`, `search()`, `delete()`, `health()`).
- **Q:** What happens if MemoryCore is offline?  
  **A:** Non-blocking graceful degradation. The memory layer enforces a 1.5s HTTP timeout and a circuit-breaker cooldown. Code generation and pipeline operations continue normally with zero exceptions thrown.

---

## Approach
1. Build `etsy_pipeline/memory/base.py` defining Pydantic schemas (`MemoryEntry`, `MemoryCategory`) and the `BaseMemoryProvider` abstract interface.
2. Implement `etsy_pipeline/memory/filter.py` to filter out terminal dumps, stack traces, and noise before capture.
3. Implement `etsy_pipeline/memory/tencent_provider.py` implementing `BaseMemoryProvider` over HTTP (`httpx`) targeting MemoryCore v3 API endpoints (`/v3/atomic/*`).
4. Implement `etsy_pipeline/memory/service.py` as the main wrapper for memory recall, prompt context formatting, and capture routing.
5. Update `etsy_pipeline/config/settings.py` with memory configuration fields (feature flag, URL, API key, timeout).
6. Provide a CLI helper (`scripts/memory_cli.py`) and a mock provider (`MockMemoryProvider`) for unit testing without external dependencies.

---

## Scope

**Files/modules touched:**
- `plans/2026-08-05-developer-memory-abstraction.md` — [NEW] Approved plan record
- `etsy_pipeline/memory/__init__.py` — [NEW] Package entry point
- `etsy_pipeline/memory/base.py` — [NEW] Interface & data models
- `etsy_pipeline/memory/filter.py` — [NEW] High-signal noise/junk filter
- `etsy_pipeline/memory/tencent_provider.py` — [NEW] HTTP provider client with circuit fallback
- `etsy_pipeline/memory/service.py` — [NEW] High-level memory service & prompt formatter
- `etsy_pipeline/config/settings.py` — [MODIFY] Memory configuration parameters
- `scripts/memory_cli.py` — [NEW] CLI helper script
- `docker/memory-core/docker-compose.yml` — [NEW] Container configuration
- `tests/test_memory_abstraction.py` — [NEW] Pytest suite

**Out of scope:**
- User/Production memory (Phase 1 is strictly for developer engineering memory)
- End-user UI integration or dashboard panels

---

## Risks & edge cases
- **MemoryCore Offline:** Handled via 1.5s timeout, circuit cooldown, and silent fallback returning empty lists.
- **Noise Pollution:** Handled via `MemoryFilter` regex and length checks.
- **Provider Lock-in:** Handled by strictly coding against `BaseMemoryProvider` ABC.

---

## Steps
1. Create `plans/2026-08-05-developer-memory-abstraction.md`.
2. Implement `etsy_pipeline/memory/base.py`.
3. Implement `etsy_pipeline/memory/filter.py`.
4. Implement `etsy_pipeline/memory/tencent_provider.py`.
5. Implement `etsy_pipeline/memory/service.py`.
6. Update `etsy_pipeline/config/settings.py`.
7. Create `scripts/memory_cli.py`.
8. Create `docker/memory-core/docker-compose.yml`.
9. Create `tests/test_memory_abstraction.py` and verify test suite passes.
10. Update graph via `python scripts/build_graph.py`.

---

## Rollback
Set `MEMORY_ENABLED=false` in `.env` or settings. Delete `etsy_pipeline/memory/` and `scripts/memory_cli.py`.
