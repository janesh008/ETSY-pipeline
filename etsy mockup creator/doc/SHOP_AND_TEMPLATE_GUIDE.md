# 📖 Complete Guide: Adding New Shops, Hero Templates & Lifestyle Mockup Surfaces

> **Target Audience:** Anyone (Technical & Non-Technical Users).  
> Follow these simple, step-by-step instructions to add a new Etsy shop, add new hero mockup templates, add new lifestyle photo surfaces, or configure multi-clipart wall art mockups.

---

## 📑 Table of Contents
1. [How to Add a New Etsy Shop](#1-how-to-add-a-new-etsy-shop)
2. [How to Add a Standard Hero JSON Template](#2-how-to-add-a-standard-hero-json-template)
3. [How to Add a New Lifestyle Photo Surface Template](#3-how-to-add-a-new-lifestyle-photo-surface-template)
4. [How to Configure Wall Art & Multi-Clipart Layouts](#4-how-to-configure-wall-art--multi-clipart-layouts)
5. [Summary Checklist](#5-summary-checklist)

---

## 1. How to Add a New Etsy Shop

Follow these **3 simple steps** to introduce a new shop into the system:

### Step 1: Create the Shop Directory
Navigate to `etsy mockup creator/rendering/shops/` and create a new folder named `shop<N>_<shop_id>`:
```
etsy mockup creator/rendering/shops/
├── shop1_pixelbarstudio/
├── shop2_luna_cliparts/
├── shop3_crisp_png_co/
└── shop4_my_new_shop/            <-- Create your new shop folder here
    ├── templates/                <-- Create subfolder for standard hero templates
    ├── metadata_prompt.txt       <-- Create SEO prompt file
    └── shop_config.yaml          <-- Create configuration file
```

### Step 2: Create `shop_config.yaml`
Create `shop_config.yaml` inside your new shop folder:

```yaml
shop_id: my_new_shop
shop_name: My New Shop Display Name
etsy_shop_name: MyEtsyShopHandle

# --- MOCKUP SETTINGS ---
mockups:
  hero:
    templates_dir: rendering/shops/shop4_my_new_shop/templates/
  lifestyle:
    enabled: true                 # Set to false if you don't want lifestyle mockups
    products:
      - name: black_t-shirt_1
        layout: single_product
      - name: white_tshirt_1
        layout: single_product
      - name: mug_1
        layout: single_product

# --- METADATA SETTINGS ---
metadata:
  prompt_file: rendering/shops/shop4_my_new_shop/metadata_prompt.txt
  seo_mode: true
```

### Step 3: Create `metadata_prompt.txt`
Create `metadata_prompt.txt` inside your shop folder containing the Etsy SEO rules for AI listing title, tags, and description generation.

---

## 2. How to Add a Standard Hero JSON Template

Standard hero templates create multi-image grid collages, title banners, and badges (e.g. 2000x2000 canvas).

### Step 1: Place JSON Template File
Save your exported `.json` template file into your shop's `templates/` folder:
`etsy mockup creator/rendering/shops/shop<N>_<shop_id>/templates/my_new_hero.json`

### Step 2: Attach Compatibility Metadata
Run this single command in your terminal to automatically attach visual compatibility metadata:

```powershell
python -c "import sys; sys.path.insert(0, 'etsy mockup creator'); from rendering.compatibility.metadata_generator import auto_generate_metadata; auto_generate_metadata('etsy mockup creator/rendering/shops/shop4_my_new_shop/templates/my_new_hero.json', product_type='tshirt', product_color='white')"
```

---

## 3. How to Add a New Lifestyle Photo Surface Template

Lifestyle surfaces display clipart printed onto real-life models, T-shirts, mugs, pillows, or frames.

### Step 1: Export Folder from Template Extraction Studio
When you generate a new surface template, ensure the exported folder contains these **4 required files**:
```
lifestyle_products/
└── <new_surface_name>/          <-- e.g., black_tshirt_v2, mug_3, poster_frame_1
    ├── blank.png                <-- Blank photo (e.g. 4000x4000)
    ├── mask.png                 <-- Print area mask (white = print region)
    ├── shadow_overlay.png       <-- Wrinkle/shadow overlay
    └── config.json              <-- Perspective corners coordinates
```

Place this folder inside:
`etsy mockup creator/rendering/lifestyle_products/<new_surface_name>/`

### Step 2: Run Auto-Group Assignment Script
Open your terminal and run:
```powershell
python scripts/assign_surface_groups.py
```
This automatically reads your folder name, infers the product color (`black`, `white`, `brown`), creates `metadata.json`, and assigns `compatibility_groups` (`light_art`, `dark_art`, `colorful_art`, `medium_art`).

### Step 3: Enable the Surface in Shop Config
Open `shop_config.yaml` of any shop where you want to use this surface, and add it under `lifestyle.products`:

```yaml
lifestyle:
  enabled: true
  products:
    - name: <new_surface_name>
      layout: single_product
```

---

## 4. How to Configure Wall Art & Multi-Clipart Layouts

Wall art surfaces display multiple clipart items (or grid arrangements) printed together on one frame/canvas.

### Step 1: Create Wall Art Surface Folder
Place your wall art frame template inside `rendering/lifestyle_products/wallart_grid_1/` with its `blank.png`, `mask.png`, `shadow_overlay.png`, and `config.json`.

### Step 2: Configure `shop_config.yaml`
In your shop's `shop_config.yaml`, specify `layout: wall_art` and `wall_art_count`:

```yaml
lifestyle:
  enabled: true
  products:
    - name: wallart_grid_1
      layout: wall_art
      wall_art_count: 6           # Number of clipart items to display in grid
```

### Step 3: Layout Strategy Handling
The system uses the **Strategy Pattern**:
- `single_product` $\to$ Uses `SingleProductLayout` (prints 1 main character)
- `wall_art` $\to$ Uses `WallArtLayout` (arranges `wall_art_count` clipart items on print canvas)

---

## 5. Summary Checklist

| Action | What File to Touch / Create | Command to Run |
| :--- | :--- | :--- |
| **Add New Shop** | Create `rendering/shops/shopX_<id>/shop_config.yaml` | None |
| **Add Hero Template** | Place `.json` in `rendering/shops/shopX_<id>/templates/` | `python -m ...metadata_generator` |
| **Add Lifestyle Surface** | Place folder in `rendering/lifestyle_products/<surface_name>/` | `python scripts/assign_surface_groups.py` |
| **Enable Surface in Shop** | Add name to `shop_config.yaml` under `lifestyle.products` | None |
| **Test Mockup Rendering** | None | `python scripts/test_lifestyle_mockup.py --shop <shop_id> --product <surface_name>` |
