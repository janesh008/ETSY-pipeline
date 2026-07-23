# Implementation Plan — Enhance Etsy Listing Generator Prompt & Description Formatting

Enhance the Etsy listing generator master prompt ([Deepseek_etsy_listing_generator_prompt.txt](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources/Deepseek_etsy_listing_generator_prompt.txt)) and description generation rules to produce beautiful, professionally structured Etsy descriptions.

---

## 1. Problem Statement & Objectives

Generated Etsy listing descriptions require visual and formatting enhancements to look high-end, clean, and structured for Etsy buyers. Specific requirements:

1. **Title Header at Top of Description:** Render the full primary Etsy listing title at the very top of the Etsy description before the Hook section.
2. **300 DPI Resolution:** Specify `300 DPI high-resolution` in the **Product Details** section.
3. **Non-Segregated Total Clipart Count:** In **Product Details → Included Files**, state the total count of PNG images directly (e.g., `22 high-resolution PNG images in a Zip file.`) without breaking down or segregating into subcategories (characters, props, patterns).
4. **Beautiful Formatting:** Structure description section headers with clean typography and visual accents (`✨`, `📦`, `💻`, `🎨`, `🌟`, `📜`, `🛒`) so listings look modern and easy to read.

---

## 2. Technical Strategy

### Prompt Updates (`Deepseek_etsy_listing_generator_prompt.txt`)
- **Step 3 (Description Rules)**:
  - **Top Banner / Title Header**: Render the full generated Etsy title at the top of the description before Section 1 (Hook).
  - **Product Details Bullets**:
    - **Included Files:** `[Exact Number from image] high-resolution PNG images in a Zip file.` *(Explicit Rule: State total count directly. Do NOT break down into sub-categories like XX characters or XX props).*
    - **Resolution:** `300 DPI high-resolution, print-ready for sublimation, printing, and digital crafts.`
  - **Section Styling**: Header accents `✨ — HOOK — ✨`, `📦 — PRODUCT DETAILS — 📦`, `💻 — HOW TO DOWNLOAD — 💻`, `🎨 — DESIGN DESCRIPTION — 🎨`, `✨ — PERFECT FOR — ✨`, `🌟 — WHY PIXEL BAR STUDIO — 🌟`, `📜 — SEO REINFORCEMENT — 📜`, `🛒 — CALL TO ACTION — 🛒`.
- **Output Format**: Update the output template to reflect title placement at top, 300 DPI resolution, direct asset count, and section header icons.
- **Quality Checklist**: Update checklist rules to enforce 300 DPI, title placement at top of description, and non-segregated total asset count.

### Worker & Parser Updates
- **`metadata_worker.py`**: Confirm description parsing cleanly captures the title header at top of the description block.
- **`tests/test_metadata_prompt_format.py`**: Unit test verifying prompt rules and parsing integrity.

---

## 3. Verification Plan

- `pytest tests/test_metadata_prompt_format.py`
- `pytest tests/test_metadata_worker.py`
- `mypy etsy_pipeline/workers/metadata_worker.py`
- `ruff check etsy_pipeline/workers/metadata_worker.py`
