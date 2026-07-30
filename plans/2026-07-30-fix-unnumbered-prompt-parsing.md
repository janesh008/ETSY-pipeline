# Plan: Support Unnumbered Prompt Files and Fix Empty Prompt Fallback

**Date:** 2026-07-30
**Status:** approved
**Related:** [etsy_pipeline/workers/CONTEXT.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/CONTEXT.md)

---

## Problem
Prompt files formatted with `## SECTION_NAME` headings but unnumbered paragraph prompt text (instead of `1. `, `2. `) result in 0 extracted prompts because `PromptWorker._extract_prompts_from_section` looks exclusively for numbered line regex (`r"^\d+\.\s+"`). Additionally, `PipelineRunnerService.create_job` checks `if not job.prompts:`, which evaluates to `False` for dictionaries containing keys with empty lists (`{"MAIN_CHARACTER": []}`), preventing fallback prompt injection and causing `ImageGenerationError: No prompts found in job`.

---

## Approach
1. In `PromptWorker._extract_prompts_from_section`:
   - First attempt numbered line extraction (`r"^\d+\.\s+"`).
   - If no numbered prompts are found, fall back to extracting unnumbered paragraph blocks separated by double newlines (`\n\n`) or paragraph breaks under the section heading.
   - Ignore header notes / inactive markers starting with `(` (e.g., `(not applicable...`) or comments starting with `#`.
   - Clean and normalize whitespace for each extracted prompt string.

2. In `PipelineRunnerService.create_job`:
   - Replace `if not job.prompts:` with `if job.total_prompt_count == 0:` when assigning fallback prompt dictionaries.

3. In `tests/test_prompt_worker.py`:
   - Add unit test `test_parse_response_unnumbered_prompts()` verifying that unnumbered prompt text files containing `## SECTION_NAME` headings are parsed properly into section prompt lists.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/workers/prompt_worker.py` — Add fallback in `_extract_prompts_from_section` to parse unnumbered paragraph blocks.
- `craftdesk_api/services/pipeline_runner.py` — Fix `create_job` fallback condition to use `job.total_prompt_count == 0`.
- `tests/test_prompt_worker.py` — Add test case for unnumbered prompt parsing.

**Out of scope:**
- Modifying prompt generation SKILL.md rules or ComfyUI API execution.

---

## Risks & edge cases
- *Section preamble containing instructions or notes*: Handled by filtering out blocks starting with `(` or `#` or containing inactive section markers.
- *Mixed multi-line paragraphs*: Whitespace is normalized (`" ".join(block.split())`).

---

## Steps
1. Modify `_extract_prompts_from_section` in `etsy_pipeline/workers/prompt_worker.py`.
2. Update fallback check in `craftdesk_api/services/pipeline_runner.py`.
3. Add unit test in `tests/test_prompt_worker.py`.
4. Run tests with `pytest tests/test_prompt_worker.py` and verify all tests pass.
5. Update living documentation in `etsy_pipeline/workers/doc/DETAILED.md` as required by AGENTS.md rules.

---

## Rollback
Revert the edits to `etsy_pipeline/workers/prompt_worker.py`, `craftdesk_api/services/pipeline_runner.py`, and `tests/test_prompt_worker.py`.
