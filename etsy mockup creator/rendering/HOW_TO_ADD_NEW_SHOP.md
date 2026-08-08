# How to Add a New Etsy Shop

Follow these 5 steps. **Zero Python code changes required.**

---

## Step 1 — Create the Shop Folder

Copy an existing shop folder as your starting point:

```bash
# In etsy mockup creator/rendering/shops/
cp -r shop2_luna_cliparts/ shop4_your_shop_name/
```

On Windows:
```powershell
Copy-Item -Recurse "rendering\shops\shop2_luna_cliparts" "rendering\shops\shop4_your_shop_name"
```

---

## Step 2 — Edit `shop_config.yaml`

Open `shop4_your_shop_name/shop_config.yaml` and update:

```yaml
shop_id: your_shop_name          # unique ID, lowercase, underscores
shop_name: YourShopDisplayName
etsy_shop_name: yourEtsyShopSlug

mockups:
  hero:
    templates_dir: rendering/shops/shop4_your_shop_name/templates/
  lifestyle:
    enabled: true                # or false if no lifestyle mockups
    products:
      - mug                      # pick from lifestyle_products/ folder names
      - tshirt_girl

metadata:
  prompt_file: rendering/shops/shop4_your_shop_name/metadata_prompt.txt
  seo_mode: true
```

---

## Step 3 — Add Hero Template(s)

Add `.json` files to `templates/`. Use the same format as `shop1_pixelbarstudio/templates/hero.json`.

Start by copying and editing:

```bash
cp rendering/shops/shop1_pixelbarstudio/templates/hero.json \
   rendering/shops/shop4_your_shop_name/templates/your_hero_style.json
```

Edit the coordinates, element count, fonts, and colors in the JSON.

The renderer (`src/renderer.py`) runs unchanged — only the template JSON changes.

---

## Step 4 — Write `metadata_prompt.txt`

This is the Gemini system instruction for how your shop's listings should be written.

**Required rules to include in every prompt:**
- Title: Must be SEO-ranked. Use real Etsy search keywords specific to the theme. Format: `[Theme] Clipart Bundle | [Use Case] PNG | [Style] Digital Download`. Max 140 chars.
- Tags: 13 tags. Each = a real Etsy search phrase. No filler. Max 20 chars each.
- Description: Starts with the most searchable sentence. Mentions theme, format, resolution, use cases.
- No generic text: Reject "Perfect for any occasion", "High quality". Must be specific.
- Add your shop's name and brand voice.

See `shop2_luna_cliparts/metadata_prompt.txt` for a reference example.

---

## Step 5 — Add Shop to the Multi-Shop Pipeline (Optional)

If you want this shop included in the multi-shop pipeline run, add it to:

```
etsy_pipeline/config/pipeline_profiles.yaml
```

Under `multi_shop.shops`:

```yaml
multi_shop:
  shops:
    - pixelbarstudio
    - luna_cliparts
    - crisp_png_co
    - your_shop_name    ← add here
```

---

## Done!

Run the multi-shop pipeline. Your new shop will be included automatically.

The pipeline reads `shop_config.yaml`, dispatches `HeroPlugin` with your templates,  
dispatches `LifestylePlugin` for your chosen products, and generates metadata using your prompt.

---

## Lifestyle Product Images

If you enabled lifestyle products, add these 3 files to each product folder in `rendering/lifestyle_products/<product>/`:

| File | What it is |
|---|---|
| `blank.png` | Professional photo of the blank product (white shirt, empty mug, etc.) |
| `mask.png` | Grayscale: white = print area, black = everything else |
| `shadow_overlay.png` | Pre-baked shadow/lighting/wrinkle texture |

The `config.json` already exists — edit the `print_area.corners` to match where your print area is in the blank photo.

Use any photo editor to find the pixel coordinates of the 4 corners of the print area (top-left, top-right, bottom-right, bottom-left).
