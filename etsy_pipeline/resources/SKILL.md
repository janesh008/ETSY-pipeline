---
name: littlenest-clipart-prompt-generator
description: "Generate image generation prompts for Pixel Bar Studio Etsy shop digital PNG clipart bundles. Output is plain text, organized under LOCKED section headings (MAIN_CHARACTER, SUB_CHARACTER_1-8, CHARACTER_COMBO_2/3/4/FULL_GROUP, PATTERN, PROP, SCENE, LOGO_EMBLEM, BANNER, ALPHABET_NUMBER, FRAME_BORDER) for automated parsing. No Python, no JSON. Covers any cartoon/character theme, single or ensemble cast; sections activate based on roster size. Each sub-character section covers only that character — never the main character. Trigger for 'generate prompts for [cartoon]', 'make prompts for [cartoon] theme', 'create clipart prompts for [cartoon]', or any casual variant like 'I need Minnie Mouse prompts' or 'stitch clipart prompts for birthday'."
---

# Pixel Bar Studio Cartoon Clipart Prompt Generator

Generates **AI image generation prompts** for Pixel Bar Studio's digital PNG clipart bundles on Etsy.

**Output format is always plain text** — one self-contained prompt per entry, separated by a blank line, organized under locked section headings. No Python code blocks, no JSON, no master prompt variable, no batch wrappers, no quote characters around prompts. Every prompt is complete and ready to paste directly into any image generation tool, and the heading structure is fixed so it can be parsed automatically by the downstream pipeline.

---

## ⚠️ CRITICAL RULES — READ BEFORE GENERATING ANYTHING

### RULE A — LOCKED SECTION HEADINGS (NEVER DEVIATE)
Only these exact heading names may ever be used, written precisely as shown — no spaces added, no extra words, no appended character names, no renumbering:

```
MAIN_CHARACTER
SUB_CHARACTER_1
SUB_CHARACTER_2
SUB_CHARACTER_3
SUB_CHARACTER_4
SUB_CHARACTER_5
SUB_CHARACTER_6
SUB_CHARACTER_7
SUB_CHARACTER_8
CHARACTER_COMBO_2
CHARACTER_COMBO_3
CHARACTER_COMBO_4
CHARACTER_COMBO_FULL_GROUP
PATTERN
PROP
SCENE
LOGO_EMBLEM
BANNER
ALPHABET_NUMBER
FRAME_BORDER
```

Each appears in the output as `## SECTION_NAME` exactly as spelled above.

❌ FORBIDDEN: `## SUB_CHARACTER_1 - Dr. Octavius SOLO`, `## SUB CHARACTERS (Angel)`, `## PROP_FOOD`, `## SCENE_INTERIOR`
✅ CORRECT: `## SUB_CHARACTER_1` (character identity lives inside each prompt, never in the heading itself)

**Inactive sections are still listed** with a one-line note underneath — `(not applicable for this roster)` — never omitted silently. This keeps the schema predictable for the automation pipeline regardless of cartoon size.

### RULE B — EACH SUB_CHARACTER / COMBO SECTION MUST BE ABOUT THE RIGHT CHARACTER(S)
This is the most common failure mode — do not repeat it.

Before generating `SUB_CHARACTER_1`, identify which roster character occupies that slot (e.g. Miles Morales) and write EVERY prompt in that section about Miles Morales. Do not default back to the main character.

**Self-check before finalizing each SUB_CHARACTER_N section:** confirm the character named in prompt 1 matches the character named in the last prompt of that section. If they don't match, regenerate the drifting prompts before moving on.

Same applies to `CHARACTER_COMBO_2` / `_3` / `_4` / `_FULL_GROUP` — every prompt must explicitly name ALL characters required for that combo tier, every time. A combo prompt naming only one character is invalid and must be rewritten.

### RULE C — IN-WORLD TERMINOLOGY ONLY
Never use generic cartoon language. Every prompt must use franchise-specific, in-world terminology — exact character names, canonical outfit/color details, and in-universe object/location names.

❌ WRONG: "cartoon character holding a stick"
✅ RIGHT: "Stitch, Experiment 626 from Lilo & Stitch, holding his ukulele"

### RULE D — CHARACTER BALANCE (NO MAIN CHARACTER DOMINANCE)
Distribute prompts proportionally across the full roster in ensemble-cast cartoons. Each character section gets roughly equal prompt count (±20%). `MAIN_CHARACTER` should not receive more than ~20–25% of the total bundle when there are 3+ characters.

### RULE E — STANDARD MINIMUM: 10 PROMPTS PER ACTIVE SECTION
Every active section (any locked key that applies to this cartoon/bundle) must receive **at least 10 prompts**, regardless of the total bundle size requested. This is a hard floor. If a requested total prompt count would push a section below 10, flag this to the user instead of silently shrinking a section under the floor.

### RULE F — ANATOMY ACCURACY (PREVENT AI LIMB ERRORS)
All character prompts must include explicit anatomy-correcting language:

**Humanoid characters:** `exactly two arms, exactly two legs, correct human anatomy, no extra limbs, no missing limbs, no floating limbs, no extra fingers, hands correctly rendered with five fingers each`

**Quadruped animals:** `exactly four legs, all four paws/hooves/feet clearly grounded, correct quadruped anatomy, no extra legs, no missing legs, no extra paws`

**Forbidden poses** (cause anatomy failures): running at speed, spinning/twirling, reaching behind own back, crossed legs while standing, extreme side angles, sitting facing away from camera.

**Safe poses:** standing upright both feet flat, sitting cross-legged, kneeling on one knee, waving with one hand at natural angle, holding object at chest height, sitting on a surface, walking slowly mid-stride, curtseying, blowing a kiss, hands clasped together.

### RULE G — TEXT SPELLING ACCURACY (FOR TEXT-IN-IMAGE PROMPTS)
For `LOGO_EMBLEM`, `BANNER`, `ALPHABET_NUMBER` sections with readable text:
- Spell exact target text using `[spell: T-E-X-T]` notation inside the prompt
- End with: `text must be in clear legible English, correct spelling, sharp crisp letterforms, no blurry letters, no distorted text, no misspelled words, no garbled characters`
- Keep in-image text to maximum 2–3 words

### RULE H — REFERENCE IMAGE / SCREENSHOT USAGE
When a screenshot is uploaded, extract its color palette, illustration density, character proportions, and composition style before writing any prompts. Embed these specifics into every prompt: `matching the watercolor clipart style shown in reference, [specific palette], [specific composition notes]`.

---

## STEP 1 — PARSE THE INPUT

Extract from user input:

| Signal | Examples |
|---|---|
| **Cartoon / theme name** | Minnie Mouse, Lilo & Stitch, Bluey, Encanto |
| **Event theme** | birthday, baby shower, Christmas, Halloween, Valentine's Day |
| **Style hint** | watercolor, 3D, flat cartoon, chibi (infer from cartoon if not given) |
| **Section requested** | "just patterns", "only props", "full bundle" (default = full bundle, all active sections) |
| **Prompt count** | "make 50 prompts", "full 200" (default = full bundle with recommended counts per section, respecting RULE E floor) |
| **Reference image** | Screenshot uploaded? → Apply RULE H |

> If no theme is given, default to **birthday**.
> If no style is given, infer from the cartoon's visual language (see STEP 3).
> If no section is specified, generate **all active sections** for the roster.

---

## STEP 2 — BUILD THE CHARACTER & WORLD ROSTER

Before writing any prompts, compile the **full universe** of the cartoon and write the roster out explicitly — do not just hold it mentally. This written roster is your source of truth for which character occupies which `SUB_CHARACTER_N` slot while generating; do not deviate from it mid-bundle.

```
MAIN_CHARACTER: [Character Name] — [canonical description: colors, outfit, signature features]
SUB_CHARACTER_1: [Character Name] — [canonical description]
SUB_CHARACTER_2: [Character Name] — [canonical description]
...
```

**Minnie Mouse example:**
- MAIN_CHARACTER: Minnie Mouse (pink polka dot dress, oversized bow)
- SUB_CHARACTER_1: Mickey Mouse
- SUB_CHARACTER_2: Daisy Duck

**Lilo & Stitch example:**
- MAIN_CHARACTER: Stitch (Experiment 626, blue alien)
- SUB_CHARACTER_1: Lilo (Hawaiian girl, red floral dress)
- SUB_CHARACTER_2: Angel (Experiment 624, pink)
- SUB_CHARACTER_3: Nani (Lilo's sister)

### Roster Size → Active Sections

| Roster Size | Active Character/Combo Sections |
|---|---|
| 1 character only | `MAIN_CHARACTER` only (no SUB, no COMBO) |
| 2 characters | + `SUB_CHARACTER_1`, `CHARACTER_COMBO_2` |
| 3 characters | + `SUB_CHARACTER_2`, `CHARACTER_COMBO_3` |
| 4 characters | + `SUB_CHARACTER_3`, `CHARACTER_COMBO_4` |
| 5+ characters | + `SUB_CHARACTER_4` through `_8` as needed, `CHARACTER_COMBO_FULL_GROUP` |

`PATTERN`, `PROP`, and `SCENE` are always active regardless of roster size.
`LOGO_EMBLEM`, `BANNER`, `ALPHABET_NUMBER`, and `FRAME_BORDER` activate only when the user asks for those product types (or see STEP 7 for when to proactively suggest them).

### World Inventory (for PROP, SCENE, PATTERN content)

Compile the cartoon's associated world into subcategories — these all feed into the single `PROP` and `SCENE` sections (no further sub-splitting of those sections):

| Subcategory | What to list |
|---|---|
| Signature objects / props | Items closely associated with the character (e.g. Minnie's bow, Stitch's ukulele) |
| Food & drinks | Foods featured in or associated with the show |
| Flowers & nature | Plants, flowers, trees iconic to the cartoon world |
| Locations / scenes | Recognizable places from the cartoon |
| Vehicles | Cars, spaceships, surfboards |
| Party / event props | Birthday cakes, balloons, cupcakes, gifts (theme-specific) |
| Pattern motifs | Polka dots, gingham, floral, character-silhouette repeat patterns |

**Minnie Mouse world inventory example:**
- Signature objects: oversized pink polka dot bow, white gloves, red/pink dress, high heels, mirror, purse
- Food: pink cupcake with bow topper, ice cream cone with bow, popsicle, macaron, birthday cake
- Flowers: daisies, pink roses, daisy bouquet
- Locations: Minnie's polka dot house, candy shop
- Vehicles: pink VW Beetle car
- Party props: pink gift box with bow, pink balloon, polka dot banner, confetti
- Pattern motifs: polka dot, gingham, floral with daisies, Minnie silhouette flowers, bow repeat, ice cream repeat, hearts & stripes

**Lilo & Stitch world inventory example:**
- Signature objects: ukulele, Ohana sign/door, surfboard, cassette tape (Stitch's Mix), Instax camera, red backpack, vintage telephone, record player
- Food: pineapple, watermelon slice, banana, coconut, peanut butter toast, rainbow popsicle, ice cream
- Flowers: blue/pink hibiscus, plumeria/frangipani, tropical monstera leaf
- Locations: Hawaiian beach, taro patch music store, bus stop, blue wooden house (wrecked), tiki stage
- Vehicles: pink spaceship, surfboard
- Party props: birthday cake, balloons, confetti, leis, tropical garlands
- Pattern motifs: surfboards, coconuts & waves, hibiscus floral, Stitch & hearts on blue, flower garland, ocean waves, Stitch scenes tossed

---

## STEP 3 — STYLE SYSTEM

### Style by Cartoon

| Cartoon | Recommended Style | Texture/Feel |
|---|---|---|
| Minnie Mouse | Soft watercolor illustration | Pastel pink palette, gentle washes, painterly edges, feminine and sweet |
| Lilo & Stitch | Soft watercolor / chibi hybrid | Soft pastels, blue & pink tones, tropical warmth, Hawaii inspired |
| Bluey | Flat 2D cartoon | Clean vector lines, bright saturated colors |
| Moana | Watercolor storybook | Warm tropical tones, painterly |
| Encanto | Vibrant 3D cartoon | Rich jewel tones, expressive |
| Generic fallback | Watercolor clipart | Soft watercolor, white background |

### Color Palette Notes

State the dominant palette inline in every prompt:

- **Minnie Mouse:** soft pink (#F9B7C1), dusty rose, white, black accents, gold
- **Lilo & Stitch:** sky blue (#A8D8EA), soft pink (#F7C5CC), mint, lavender, warm sand, hibiscus red

---

## STEP 4 — PROMPT TEMPLATES PER SECTION

### MAIN_CHARACTER / SUB_CHARACTER_N
```
[CHARACTER NAME], [canonical description — colors, outfit, signature features], [pose from RULE F safe pose bank], [prop clearly described, in-universe name], [prop reinforced a second time from a different angle], face forward, [specific expression], full body visible from head to toe, [anatomy correction phrase per RULE F], soft watercolor illustration style, pastel [COLOR] palette, isolated subject, pure white background, no text, no watermark, no background elements
```

### CHARACTER_COMBO_2 / _3 / _4 / _FULL_GROUP
```
[CHARACTER A name + canonical description] and [CHARACTER B name + canonical description] [and CHARACTER C... for larger combos], [interaction type: hugging / high-fiving / sitting side by side / sharing a prop], [prop if any], all characters fully visible from head to toe, facing forward or three-quarter view, [expression for each], [anatomy correction phrase for each per RULE F], soft watercolor illustration style, [color palette], isolated subject, pure white background, no text, no watermark
```

### PATTERN
```
Seamless repeat pattern, [pattern elements, in-universe themed] in [tossed/stripe/grid] layout, [color palette], soft watercolor illustration style, [background color] background, no characters, no text, no watermark, evenly spaced, tileable
```

### PROP
```
[Object name, in-universe term], isolated clipart, centered, [key visual detail — color, decoration, texture], soft watercolor illustration style, [color palette], white background, no characters, no text, no watermark
```

### SCENE
```
[In-universe location name], [key visual details], soft watercolor illustration style, [color palette], dreamy and painterly, gentle soft lighting, no characters in foreground, no text, no watermark
```
Scene prompts may include a painted background (the only section where this is allowed) — they still exclude characters in foreground, text, and watermark.

### LOGO_EMBLEM / BANNER / ALPHABET_NUMBER / FRAME_BORDER
Apply RULE G (text spelling accuracy) strictly. Each prompt = one variation (color/size/decoration variant).

---

## STEP 5 — FULL BUNDLE DISTRIBUTION GUIDE

Every active section has a hard floor of **10 prompts minimum** (RULE E), regardless of total bundle size requested.

**Single-character cartoon (130 total):**
`MAIN_CHARACTER`: 60–70 | `PATTERN`: 20 | `PROP`: 25–30 | `SCENE`: 10–15

**2-character cartoon (130 total):**
`MAIN_CHARACTER`: 30 | `SUB_CHARACTER_1`: 25 | `CHARACTER_COMBO_2`: 20 | `PATTERN`: 15 | `PROP`: 25 | `SCENE`: 15

**4-character cartoon (160 total):**
`MAIN_CHARACTER`: 25 | `SUB_CHARACTER_1/2/3`: 20 each | `CHARACTER_COMBO_4`: 15 | `PATTERN`: 15 | `PROP`: 20 | `SCENE`: 15

Scale proportionally for other roster sizes. Keep `MAIN_CHARACTER` ≤ 25% of total in multi-character bundles (RULE D). Never let any active section drop below the 10-prompt floor — if a requested total can't support that, flag it to the user.

> **Etsy bundle tip:** Bundles with 100+ PNGs sell better. Patterns + props add count without needing more character generation. Always include all active sections for a premium-feeling bundle.

---

## STEP 6 — GENERATE THE OUTPUT

**Output is always plain text — numbered prompts separated by blank lines. No Python, no JSON, no code blocks, no quote characters wrapping prompts.**

Each section starts with the exact locked heading (RULE A). Each prompt is numbered and on its own line, with one blank line between prompts. Every prompt ends with the full inline exclusion phrase.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨 LittleNest PROMPT BATCH — [CARTOON] | [THEME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## MAIN_CHARACTER

1. [full self-contained prompt, ending with inline exclusions and pure white background]

2. [full self-contained prompt]

...

## SUB_CHARACTER_1

[N]. [full self-contained prompt — all about this one roster character]

...

## CHARACTER_COMBO_2

[N]. [full self-contained prompt — names all required characters]

...

## PATTERN

[N]. [full self-contained prompt]

...

## PROP

[N]. [full self-contained prompt]

...

## SCENE

[N]. [full self-contained prompt — may include painted background]

## LOGO_EMBLEM
(not applicable for this roster)

## BANNER
(not applicable for this roster)

## ALPHABET_NUMBER
(not applicable for this roster)

## FRAME_BORDER
(not applicable for this roster)
```

**Plain text rules for every prompt:**
- ✅ One complete line of plain text — no Python, no quotes wrapping the prompt, no brackets
- ✅ Separated by a single blank line
- ✅ Numbered sequentially within each section
- ✅ Every character/object prompt ends with: `no background, no environment, no text, no watermark, no frame, no room, no wall, no multiple characters, pure white background`
- ✅ Every pattern prompt ends with: `no characters, no text, no watermark, tileable`
- ✅ No `master_prompt =`, `negative_prompt =`, `batch_N = [...]`, or any Python/JSON syntax

---

## COMPLETE WORKED EXAMPLE — Lilo & Stitch, Birthday Theme (abbreviated)

```
## MAIN_CHARACTER

1. Stitch, Experiment 626 from Lilo & Stitch, blue alien with large ears and koala-like features, sitting upright holding a colorful birthday cake with lit candles in both paws, birthday cake prominently visible and centered, face forward, wide toothy smile, eyes sparkling and defined, full body visible from head to toe, exactly four legs, all four paws clearly grounded, correct quadruped anatomy, no extra legs, no missing legs, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark, no background elements

2. Stitch, Experiment 626, wearing a party hat centered between his large ears, sitting cross-legged, party hat clearly visible, arms resting on knees, face forward, playful toothy grin, tongue slightly out, full body visible from head to toe, exactly four legs, all four paws clearly grounded, correct quadruped anatomy, soft watercolor illustration style, soft blue and pink palette, isolated subject, pure white background, no text, no watermark

## SUB_CHARACTER_1

1. Lilo Pelekai, Hawaiian girl with dark hair in two buns, wearing her red floral dress, standing upright holding a cluster of pastel balloons on strings in her right hand, balloons clearly visible floating above her hand, face forward, wide open excited smile, full body visible from head to toe, exactly two arms, exactly two legs, correct human anatomy, no extra limbs, hands correctly rendered with five fingers each, soft watercolor illustration style, warm tropical pastel palette, isolated subject, pure white background, no text, no watermark, no background elements

2. Lilo Pelekai, in her red floral dress, carrying a large pink wrapped gift box with a ribbon bow, gift box clearly held in both arms at chest, standing upright facing forward, barefoot, face forward, happy grin eyes sparkling, full body visible from head to toe, exactly two arms, exactly two legs, correct human anatomy, no extra limbs, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

## CHARACTER_COMBO_2

1. Stitch, Experiment 626, and Lilo Pelekai in her red floral dress, sitting side by side sharing a slice of birthday cake, both characters fully visible head to toe, facing forward, Stitch with a toothy grin and Lilo with a wide happy smile, Stitch with exactly four legs and correct quadruped anatomy, Lilo with exactly two arms exactly two legs and correct human anatomy, soft watercolor illustration style, pastel blue and tropical pink palette, isolated subject, pure white background, no text, no watermark

## PATTERN

1. Seamless repeat pattern, blue hibiscus flowers and pink hibiscus flowers tossed layout with small tropical leaves, pastel blue pink and white palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

## PROP

1. Ukulele with floral hibiscus decoration on the body, isolated clipart, centered, warm honey wood color, pink and blue flower detail, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

## SCENE

1. Hawaiian beach scene, soft turquoise ocean meeting golden sand shore, palm trees on the sides, rainbow in the sky, plumeria flowers scattered on sand, dreamy soft light, watercolor illustration style, tropical pastel palette, no characters in foreground, no text, no watermark

## LOGO_EMBLEM
(not applicable for this roster)

## BANNER
(not applicable for this roster)

## ALPHABET_NUMBER
(not applicable for this roster)

## FRAME_BORDER
(not applicable for this roster)
```

---

## QUALITY CHECKLIST — Before Finalizing Output

### Structural checks (run first):
- [ ] All locked section headings present exactly as spelled in RULE A — including inactive ones marked `(not applicable for this roster)`
- [ ] No heading has appended text, character names, or descriptions in the heading itself
- [ ] Every active section has **at least 10 prompts** (RULE E hard floor) — recount each section before delivering
- [ ] Each `SUB_CHARACTER_N` section: first prompt vs last prompt name the same character (RULE B self-check)
- [ ] Each `CHARACTER_COMBO_N` prompt names all required characters for that tier
- [ ] `MAIN_CHARACTER` ≤ ~25% of total prompt count in multi-character bundles (RULE D)
- [ ] If a reference image was uploaded, its palette/style/composition notes are embedded in every prompt (RULE H)
- [ ] Any text-bearing prompt (LOGO_EMBLEM/BANNER/ALPHABET_NUMBER) uses `[spell: ...]` notation and the legibility clause (RULE G)

### Every character prompt must have ALL of:
- [ ] Character name + clear description of their signature look
- [ ] Prop (themed to event) clearly named
- [ ] Prop reinforced a second time (described from a different angle)
- [ ] Stance / orientation (facing forward)
- [ ] Face: forward-facing + specific expression (not just "smiling")
- [ ] Full body visible from head to toe
- [ ] Anatomy correction phrase matching body type (RULE F)
- [ ] Style tag (watercolor / soft illustration)
- [ ] White background

### Every pattern prompt must have:
- [ ] "Seamless repeat pattern" opener
- [ ] Elements named clearly with tossed/stripe/grid layout specified
- [ ] Color palette named
- [ ] "No characters, no text, no watermark"
- [ ] "Tileable" at the end

### Every prop prompt must have:
- [ ] Object name + key visual detail (color, decoration, material)
- [ ] "Isolated clipart, centered"
- [ ] Style tag
- [ ] "White background, no characters, no text, no watermark"

### Avoid:
- [ ] Repeating the same pose/prop across multiple prompts
- [ ] Requesting readable multi-word sentences as in-image text outside LOGO_EMBLEM/BANNER/ALPHABET_NUMBER
- [ ] Gallery/mockup/wall display language
- [ ] Forbidden poses listed in RULE F

---

## BRAND NOTES

- **Shop:** LittleNest (digital PNG clipart bundles on Etsy)
- **Target buyers:** Parents, party planners, crafters — primarily baby/kids themed events
- **Primary categories:** Baby onesie designs + digital clipart bundles
- **Art style signature:** Soft watercolor, pastel tones, sweet and feminine aesthetic (adapt for action/sci-fi themes with bolder palettes)
- **Output use:** PNG clipart bundles → digital download Etsy listings, parsed automatically by the Python pipeline into folders per section
- **Key requirement:** All character/prop prompts → white background only
- **Scene prompts:** May have illustrated backgrounds (watercolor painted)
- **Default theme:** Birthday (highest Etsy demand)
- **Copyright note:** Use character names in prompts for AI generation reference only — position Etsy listings as "inspired by" or fan-style clipart art

---

## EXTRA ETSY PRODUCT IDEAS TO SUGGEST WHEN RELEVANT

When the user asks for ideas to expand their digital product line for a theme, suggest these — note that several map directly onto the `LOGO_EMBLEM`, `BANNER`, `ALPHABET_NUMBER`, and `FRAME_BORDER` sections:

1. **Alphabet & number clipart set** (`ALPHABET_NUMBER`) — A–Z and 0–9 in themed cartoon style
2. **Name banner / pennant** (`BANNER`) — blank label styled to cartoon palette
3. **Decorative frames / borders** (`FRAME_BORDER`) — themed frame for photos or text
4. **Logo / emblem badge** (`LOGO_EMBLEM`) — franchise-style crest or badge motif
5. **Birthday invitation template** — Canva-editable, character featured
6. **Thank you card design** — small 4x6 with character
7. **Cupcake toppers** — 12-per-sheet printable rounds/squares
8. **Favor hang tags** — small punched tag with character face
9. **Water bottle label** — 8.5x2 inch wrap label
10. **Digital scrapbook paper pack** — 12x12 inch 300dpi versions of the seamless patterns
11. **Character face sticker sheet** — expressions only, 20–30 per sheet, great for planners
12. **Clip art bundle mega pack** — combine characters + props + patterns into one premium listing at 2–3x price

> Each of these can be a **separate Etsy listing** or **bundled** as a "mega bundle" at a higher price point.
