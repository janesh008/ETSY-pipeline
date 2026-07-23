# Bug Resolver — Fix Hero Mockup Center Text Theme Name Interpolation

Resolved an issue where `Hero.png` center text (`{theme_name_title}`) rendered as `"No Bg"` instead of the actual theme name or theme slug.

---

## 1. Problem Statement & Root Cause

When `mockup_worker.py` runs the `etsy mockup creator` subprocess, it points `--theme` to the local transparent images directory (e.g. `output/2026-07-24/wonder_woman_clipart/no_bg`).

Inside `etsy mockup creator/src/generator.py`, the generator resolves the theme name by inspecting the directory name (`path_obj.name`), which evaluates to `"no_bg"`. While the generator possessed logic to check if a directory was a known subfolder and fall back to its parent folder name (`path_obj.parent.name`), `"no_bg"` (and variants like `"no bg"`, `"no-bg"`, `"nobg"`) were missing from the subfolder check tuple.

Consequently:
- `theme_folder_name` remained `"no_bg"`.
- `clean_name` evaluated to `"no_bg"`.
- `theme_name` evaluated to `"no bg"`.
- `{theme_name_title}` in `hero.json` rendered as **`"No Bg"`**.

---

## 2. Implementation Plan & Strategy

To ensure absolute robustness in both automated pipeline execution and standalone CLI / web editor usage, a **two-layered defense** strategy was implemented:

1. **Automatic Directory Resolution (Fallback Layer):**
   Update the known subfolders check tuple in `generator.py` and `server.py` to include `"no_bg"`, `"no bg"`, `"no-bg"`, `"nobg"`. When the input directory is any of these, automatically climb to `path_obj.parent.name` (`<theme_slug>`) and clean it up (removing trailing numbers and replacing underscores with spaces).

2. **Explicit CLI Argument (Override Layer):**
   Add a `--theme-name` CLI parameter to `main.py` and forward it to `Generator.generate_all()`. Update `mockup_worker.py` in `etsy_pipeline` to explicitly pass `job.theme` (or `job.theme_slug.replace("_", " ")`) via `--theme-name`.

---

## 3. Code Modifications

### Etsy Mockup Creator

#### [generator.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/src/generator.py)
- Updated `Generator.generate_all()` signature to accept optional `theme_name: str | None = None`.
- Expanded the subfolder fallback check tuple:
  ```python
  if theme_folder_name.lower() in (
      "no_bg", "no bg", "no-bg", "nobg",
      "processed_no_bg", "processed no bg", "processed-no-bg",
      "misc_category", "scen-pattern"
  ):
      theme_folder_name = path_obj.parent.name
  ```

#### [main.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/src/main.py)
- Added `--theme-name` CLI argument to `ArgumentParser`.
- Passed `theme_name=args.theme_name` into `Generator.generate_all()`.

#### [server.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy%20mockup%20creator/web_editor/server.py)
- Updated the subfolder detection tuple to include `"no_bg"` variants for consistency across web editor live previews.

---

### Etsy Pipeline Workers

#### [mockup_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/mockup_worker.py)
- Updated `_run_mockup_creator()` call signature and implementation to pass `--theme-name` built from `job.theme` (falling back to `job.theme_slug.replace("_", " ")`).

---

### Unit Tests

#### [test_mockup_theme_name.py](file:///d:/Janesh/ETSY/ETSY-pipeline/tests/test_mockup_theme_name.py)
- Created unit tests verifying:
  1. Automatic resolution of `wonder_woman_clipart` from `.../wonder_woman_clipart/no_bg`.
  2. Explicit CLI `--theme-name` override behavior.

---

## 4. Verification & Validation

- **Static Analysis / Type Check:** `mypy etsy_pipeline/workers/mockup_worker.py` returned 0 errors.
- **Code Linting:** `ruff check etsy_pipeline/workers/mockup_worker.py` passed cleanly.
- **Automated Tests:** `pytest tests/test_mockup_theme_name.py` passed 2/2 tests in 0.31s.
