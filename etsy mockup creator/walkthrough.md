# Walkthrough: Hero Mockup Fixes

## Two Problems Fixed

### Problem 1: Category Name Mismatch (Previous Fix)
`hero.json` uses abstract names (`character`, `combo`, `prop`) but files use fine-grained names (`MAIN_CHARACTER`, `CHARACTER_COMBO_2`, etc.) → hero was always skipped.

### Problem 2: Sequential Pointer Exhaustion (This Fix)
The `category_pointers` system advances sequentially across ALL template renders. Earlier templates (main_character, sub_character_1, etc.) consume images from the pool before the hero gets a chance. If a category has only 10 images and 9 are consumed, the hero can't fill its slots.

---

## Changes Made

### 1. [image_loader.py](file:///d:/Janesh/etsy%20mockup%20creator/src/image_loader.py#L63-L86) — Aggregate Pools
Merges fine-grained categories into abstract pools:
- `character` ← `main_character` + all `sub_character_*`
- `combo` ← all `character_combo_*`

### 2. [generator.py](file:///d:/Janesh/etsy%20mockup%20creator/src/generator.py#L69-L81) — Hero Fallback
If hero is missing `combo` or `prop`, fills those slots with `character` images instead of skipping.

### 3. [renderer.py](file:///d:/Janesh/etsy%20mockup%20creator/src/renderer.py#L94-L124) — Hero Random Selection ⭐ NEW
Two rendering modes now exist:

| Mode | Used By | How It Works |
|---|---|---|
| **Standard** | All other templates | Sequential pointer-based. Advances through the pool to avoid duplicates across mockups. |
| **Hero** | `hero.json` only | `random.sample()` from the **full pool**. Ignores pointers entirely. Picks unique random images per render. |

Key behaviors of Hero mode:
- **Accesses ALL images** — not limited by what earlier templates consumed
- **No duplicates within one hero** — uses `random.sample()` for unique picks
- **Graceful overflow** — if more slots than images, fills extras with `random.choices()`
- **Does NOT advance pointers** — hero is independent, doesn't affect other templates

### 4. [generator.py](file:///d:/Janesh/etsy%20mockup%20creator/src/generator.py#L87-L93) — Pass Template Name
Added `template_name=template_file` to the `Renderer.render_template()` call so the renderer knows which template is being rendered.

---

## How It Works End-to-End

```
1. Image Loader scans theme folder
   → Builds: main_character(24), sub_character_1(13), prop(12), pattern(12), scene(10), ...
   → Aggregates: character(37 merged), combo(22 merged)

2. Generator loops through templates:
   a. main_character.json → Standard mode → uses images 0-8 from main_character pool
   b. sub_character_1.json → Standard mode → uses images 0-8 from sub_character_1 pool
   c. pattern.json → Standard mode → uses images 0-8 from pattern pool
   d. hero.json → HERO MODE → random.sample() picks 9 from character(37), 7 from combo(22), 5 from prop(12)
      → ALL 37 character images are available, not just leftovers!
```

## Files Changed
- [image_loader.py](file:///d:/Janesh/etsy%20mockup%20creator/src/image_loader.py) — aggregate pools
- [generator.py](file:///d:/Janesh/etsy%20mockup%20creator/src/generator.py) — hero fallback + pass template_name
- [renderer.py](file:///d:/Janesh/etsy%20mockup%20creator/src/renderer.py) — hero random selection mode
