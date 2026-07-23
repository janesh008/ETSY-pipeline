# Plan: Enhance Etsy Listing Generator Prompt & Description Formatting

**Date:** 2026-07-24
**Status:** approved
**Related:** [etsy_pipeline/workers/CONTEXT.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/CONTEXT.md)

---

## Problem
Generated Etsy listing descriptions need formatting improvements for aesthetics, visual structure, and Etsy buyer clarity. Specific updates required:
1. Include 300 DPI under Resolution in Product Details.
2. State the total clipart asset count directly in Included Files without segregating/breaking down into subcategories.
3. Place the generated Etsy listing title at the top of the Etsy description before the Hook.
4. Enhance section header styling for beautiful presentation.

---

## Approach
Update `Deepseek_etsy_listing_generator_prompt.txt` master prompt resource:
- **Title Header at Top:** Add Section 0 / Top Banner instructing LLM to output the full generated Etsy title at the top of the description.
- **Product Details Bullets:**
  - `Resolution: 300 DPI high-resolution, print-ready for sublimation, printing, and digital crafts.`
  - `Included Files: [Exact Number from image] high-resolution PNG images in a Zip file.` (With explicit negative constraint prohibiting breakdown into sub-items).
- **Aesthetic Section Headers:** Style headers with visual accents (e.g. `✨ — HOOK — ✨`, `📦 — PRODUCT DETAILS — 📦`, `💻 — HOW TO DOWNLOAD — 💻`, etc.).
- **Master Prompt Verification & Output Format:** Update Output Format template and Pre-Output Quality Checklist.
- **Metadata Worker:** Validate parser compatibility and add unit tests.

---

## Scope

**Files/modules touched:**
- `etsy_pipeline/resources/Deepseek_etsy_listing_generator_prompt.txt` — Master prompt update.
- `etsy_pipeline/workers/metadata_worker.py` — Validate description parsing.
- `tests/test_metadata_prompt_format.py` — Unit tests for prompt format and rules.
- `etsy_pipeline/workers/doc/new_features/implementation_plan_etsy_listing_description_formatting.md` — Feature documentation.
- `etsy_pipeline/workers/doc/DETAILED.md` — Documentation index update.

---

## Risks & edge cases
- Description regex parser in `metadata_worker.py` — Ensure `re.search(r"###\s*📝\s*ETSY DESCRIPTION\s*\n+(.*?)(?=###\s*🔖|\Z)", ...)` correctly captures the Title at top without trimming.
- Character limit validation — Ensure total description length stays under Etsy limit (60,000 chars, usually ~2,000 chars).

---

## Steps
1. Save plan to `plans/` and document in `etsy_pipeline/workers/doc/new_features/`.
2. Update `Deepseek_etsy_listing_generator_prompt.txt`.
3. Verify `metadata_worker.py` parsing logic.
4. Add unit test `tests/test_metadata_prompt_format.py` and run tests.
5. Run linting (`ruff check . --fix`) and type checking (`mypy etsy_pipeline`).
