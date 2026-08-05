# Plan: Integrate Developer Memory Context Recall into AGENTS.md Guidelines

**Date:** 2026-08-05
**Status:** approved
**Related:** [AGENTS.md](file:///d:/Janesh/ETSY/ETSY-pipeline/AGENTS.md)

---

## Problem
The user clarified that the developer memory database should only serve the developer/agent perspective (for pair programming and coding guidance) and should not be integrated into the actual Etsy runtime application code (`prompt_worker.py` or `metadata_worker.py`). We need to document a rule in the developer instruction set (`AGENTS.md`) so that agents automatically query the local MemoryCore Gateway for relevant guidelines and past decisions before planning or writing code.

---

## Proposed Changes

### [MODIFY] [AGENTS.md](file:///d:/Janesh/ETSY/ETSY-pipeline/AGENTS.md)
- Add a new section under "Development Workflow — Plan Before Code" called "Developer Memory Recall Guideline".
- Instruct the agent to query `python scripts/memory_cli.py recall "<search term>"` or `MemoryService.recall(query)` using context keywords from the user's prompt (e.g. filenames, topics) before starting any feature planning or code changes.
- Add instructions on how to capture developer decisions using `python scripts/memory_cli.py capture "<fact>" --category <category>` at the end of a task to keep the memory core fresh.

---

## Verification Plan

### Automated Tests
- None required (documentation-only change).

### Manual Verification
- Verify that the instructions are clearly laid out in `AGENTS.md`.
