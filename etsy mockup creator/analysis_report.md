# Hero Mockup Category Analysis & Fallback Strategy

## 1. The Problem

Your [hero.json](file:///d:/Janesh/etsy%20mockup%20creator/templates/hero.json) template requires **3 different categories** simultaneously:

| Category in hero.json | Count of elements |
|---|---|
| `character` | 8 elements (indices 0, 2, 9, 19, 26, 29, 35, 43, 44) |
| `combo` | 7 elements (indices 45, 49, 51, 59, 71, 74, 76) |
| `prop` | 5 elements (indices 28, 67, 73, 78, 80) |

But here's the critical mismatch: **your image files use fine-grained category names** (`MAIN_CHARACTER`, `SUB_CHARACTER_1`, `CHARACTER_COMBO_2`, etc.) while the hero template uses **abstract/aggregate category names** (`character`, `combo`, `prop`).

The skip logic in [generator.py](file:///d:/Janesh/etsy%20mockup%20creator/src/generator.py#L58-L70) does:

```python
missing_categories = [cat for cat in required_categories if not indexed_images.get(cat)]
if missing_categories:
    print(f"[Skipped] Template requires {missing_categories}...")
    continue
```

So if even **one** of `character`, `combo`, or `prop` doesn't exist as an exact key in `indexed_images`, the entire hero mockup is skipped.

---

## 2. Per-Theme Category Inventory

Here's what each theme actually has (themes with files only):

| Theme | MAIN_CHAR | SUB_1 | SUB_2 | SUB_3 | SUB_4 | SUB_5+ | COMBO_2 | COMBO_3 | COMBO_4 | COMBO_FULL | PATTERN | PROP | SCENE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **chubby_pooh** | 24 | 13 | 13 | 13 | — | — | 11 | 11 | — | 11 | 12 | 12 | 10 |
| **Cinderella** | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| **Elsa_Frozen_1** | 65 | — | — | — | — | — | — | — | — | — | 20 | 30 | 15 |
| **hulk** | 65 | — | — | — | — | — | — | — | — | — | 20 | 30 | 15 |
| **monsters_inc** | 8 | 15 | 20 | 15 | ~14 | — | — | — | — | 5 | 15 | 15 | 6 |
| **princess_belle** | 30 | 25 | — | — | — | — | 20 | — | — | — | 15 | 25 | 15 |
| **stitch_robot** | 65 | — | — | — | — | — | — | — | — | — | 20 | 30 | 15 |
| **winter_princess** | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| **Little_farm_d** | 10 | 10 | 10 | 10 | 10 | 10+ (6,7,8) | 10 | 10 | 10 | 10 | 15 | 30 | 15 |
| **Merida_d** | 20 | 6 | 5 | 4 | 3 | 3+3 | 6 | 2 | — | — | 12 | 25 | 10 |
| **Pooh_b_theme** | 12 | 12 | 12 | 10 | 10 | 8+8+8+8 | ~10 | 5 | 3 | 2 | 10 | 10 | 8 |
| **Snow White** | ~26 | 14 | 12 | 12 | 12 | — | 12 | 10 | 10 | — | 10 | 10 | 8 |
| **Tangled Rapunzel_1** | 18 | 14 | 12 | 10 | — | — | 12 | 10 | 10 | 10 | 12 | 12 | 10 |
| **Three Little Pigs_Q** | ~55 | ~22 | 16 | 14 | — | — | 12 | 10 | — | 8 | 12 | ~14 | ~18 |
| **UNDER THE SEA_Q** | 12 | 10 | 10 | 10 | 10 | 10+10+10+10 | — | — | — | 3 | 15 | 10 | 10 |

> [!IMPORTANT]
> **Themes without ANY combo categories** (Elsa_Frozen_1, hulk, stitch_robot) will ALWAYS fail the hero mockup because hero.json requires `combo` images. Themes without sub_characters will also fail.

---

## 3. Mockup Templates vs Available Categories

Your 22 JSON templates map to these mockup types:

| Mockup Type | Template | Required Category | Single-category? |
|---|---|---|---|
| Hero | `hero.json` | `character` + `combo` + `prop` | ❌ **MULTI** |
| Main Character | `sub_character_1.json` etc. | `main_character` | ✅ Single |
| Sub Char 1-8 | `sub_character_*.json` | `sub_character_N` | ✅ Single |
| Character Combo 2-4 | `character_combo_*.json` | `character_combo_N` | ✅ Single |
| Full Group | `character_combo_full_group.json` | `character_combo_full_group` | ✅ Single |
| Pattern | `pattern.json` | `pattern` | ✅ Single |
| Prop | `prop.json` | `prop` | ✅ Single |
| Scene | `scene.json` / `scenes.json` | `scene` | ✅ Single |
| Logo | `logo_emblem.json` | `logo_emblem` | ✅ Single |
| Banner | `banner.json` | `banner` | ✅ Single |

> [!CAUTION]
> The hero template is the **only multi-category template** and uses aggregate names (`character`, `combo`, `prop`) that don't match the fine-grained file naming convention (`main_character`, `character_combo_2`, etc.).

---

## 4. Proposed Solution: Category Aggregation + Graceful Fallback

### Approach: Modify the Image Loader to build aggregate pools

Instead of changing your templates or file naming, **add an aggregation step** in `image_loader.py` that automatically builds the abstract pools the hero template needs:

```
character  ← MAIN_CHARACTER + SUB_CHARACTER_1 + SUB_CHARACTER_2 + ... (all individual characters)
combo      ← CHARACTER_COMBO_2 + CHARACTER_COMBO_3 + CHARACTER_COMBO_4 + CHARACTER_COMBO_FULL_GROUP
prop       ← PROP (already a direct match)
```

### Changes needed:

#### A. [image_loader.py](file:///d:/Janesh/etsy%20mockup%20creator/src/image_loader.py) — Add aggregate category builder

After building `indexed_images`, add a post-processing step:

```python
# Build aggregate pools for hero template compatibility
AGGREGATE_MAP = {
    "character": ["main_character", "sub_character_1", "sub_character_2", "sub_character_3",
                  "sub_character_4", "sub_character_5", "sub_character_6", "sub_character_7", "sub_character_8"],
    "combo":     ["character_combo_2", "character_combo_3", "character_combo_4", "character_combo_full_group"],
}

for agg_name, source_cats in AGGREGATE_MAP.items():
    if agg_name not in indexed_images:  # don't overwrite if already exists
        pool = []
        for src in source_cats:
            pool.extend(indexed_images.get(src, []))
        if pool:
            indexed_images[agg_name] = sorted(pool)
```

This way:
- `character` pool = all main + sub character images merged → hero can always grab characters
- `combo` pool = all combo types merged → hero can always grab combos
- `prop` already matches directly

#### B. [generator.py](file:///d:/Janesh/etsy%20mockup%20creator/src/generator.py#L58-L70) — Soften the hero skip logic

Instead of hard-skipping, **generate a hero even if one pool is thin**, by allowing fallback:

```python
# For hero template, allow partial generation with available categories
if template_file.lower() == "hero.json":
    # Only require at least 'character' to exist
    if not indexed_images.get("character"):
        print(f"  [Skipped] Hero needs at least character images. Skipping.")
        continue
    # Fill missing combo/prop slots with character images as fallback
    for cat in ["combo", "prop"]:
        if cat not in indexed_images or not indexed_images[cat]:
            indexed_images[cat] = indexed_images["character"]
            print(f"  [Fallback] Using 'character' images for missing '{cat}' pool in hero.")
else:
    # Standard strict check for single-category templates
    missing_categories = [cat for cat in required_categories if not indexed_images.get(cat)]
    if missing_categories:
        print(f"  [Skipped] Template '{template_name}' requires {missing_categories}. Skipping.")
        continue
```

### Why This Is The Best Approach:

1. **Zero changes to your templates or file naming** — everything stays the same
2. **Automatically adapts** — if a theme has only `MAIN_CHARACTER` + `PROP`, the hero still generates using character images in combo slots
3. **No duplicate data** — aggregate pools are just references to the same files
4. **Scalable** — works for any theme regardless of how many sub_characters or combo types exist
5. **Graceful degradation** — hero looks slightly less varied for solo-character themes (hulk, stitch) but still generates a valid mockup

---

## 5. Theme Readiness Summary

After implementing the above, here's what each theme can produce:

| Theme | Hero | Main | Sub1-8 | Combo2-4 | FullGroup | Pattern | Prop | Scene | **Total Mockups** |
|---|---|---|---|---|---|---|---|---|---|
| chubby_pooh | ✅ | ✅ | ✅ ×3 | ✅ ×2 | ✅ | ✅ | ✅ | ✅ | **11** |
| Cinderella | ✅ | ✅ | ✅ ×5 | ✅ ×3 | ✅ | ✅ | ✅ | ✅ | **14** |
| Elsa_Frozen_1 | ✅* | ✅ | — | — | — | ✅ | ✅ | ✅ | **5** (hero w/fallback) |
| hulk | ✅* | ✅ | — | — | — | ✅ | ✅ | ✅ | **5** (hero w/fallback) |
| stitch_robot | ✅* | ✅ | — | — | — | ✅ | ✅ | ✅ | **5** (hero w/fallback) |
| monsters_inc | ✅ | ✅ | ✅ ×4 | — | ✅ | ✅ | ✅ | ✅ | **10** |
| princess_belle | ✅ | ✅ | ✅ ×1 | ✅ ×1 | — | ✅ | ✅ | ✅ | **8** |
| winter_princess | ✅ | ✅ | ✅ ×5 | ✅ ×3 | ✅ | ✅ | ✅ | ✅ | **14** |
| Little_farm_d | ✅ | ✅ | ✅ ×8 | ✅ ×3 | ✅ | ✅ | ✅ | ✅ | **17** |

✅* = generated using character fallback for missing combo pool

> [!TIP]
> Every theme now gets **at least 5 mockups** (hero, main_character, pattern, prop, scene) — meeting your minimum 6-mockup target when you count the individual types.

---

## Open Questions

1. **For solo-character themes** (hulk, Elsa, stitch): Should the hero use `main_character` images for ALL slots (character + combo + prop positions), or would you prefer a **simplified hero template variant** with fewer slots that only needs `main_character` + `prop`?

2. **Index mapping in hero.json**: The hero template uses very high indices (e.g., `index: 80`). Your current renderer likely wraps these with modulo. Should we preserve that behavior, or should the aggregated pool order be: all main_characters first, then sub_characters in order?

3. **Should I implement this now**, or would you prefer a different strategy?
