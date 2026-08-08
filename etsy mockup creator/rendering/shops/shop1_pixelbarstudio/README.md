# Shop 1 — PixelBarStudio

**Status:** ✅ Production — Active  
**Etsy Shop:** pixelbarstudio

## What This Shop Uses

- **Hero mockups:** All 24 existing templates in `templates/` (the original set)
- **Lifestyle mockups:** Not enabled
- **Metadata:** Default Gemini prompt (existing, unchanged)

## Templates

The `templates/` folder contains the **exact same 24 JSON files** that were previously at  
`etsy mockup creator/templates/`. They are untouched — only their location changed.

## Adding New Templates for This Shop

1. Create a new `.json` file in `templates/` using the same schema as `hero.json`
2. The pipeline will automatically pick it up on the next run

## Changing Metadata Style

Edit `shop_config.yaml` → set `metadata.prompt_file` to a `.txt` file path  
containing the new Gemini system prompt.
