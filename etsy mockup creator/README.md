# Automated Etsy Mockup Generator

An object-oriented, highly configurable Python tool built to automatically generate premium Etsy mockup listings from transparent PNG assets and JSON templates. No more Canva manual workflows!

## Key Features

- **Decoupled Configuration**: All layout, text positions, typography, borders, drop shadows, and category mapping are configured in JSON. Zero Python code modifications needed to add or modify templates.
- **Dynamic Asset Allocation**: Safely maps, scales, and wraps folder categories of images dynamically so the templates look perfect even with differing asset counts.
- **Premium Effects (Pillow)**:
  - High-quality scaling maintaining aspect ratios.
  - Transparent PNG outline border dilation (no jagged edges).
  - Offset, blurred soft drop shadows.
  - Rotations.
- **Variable Interpolation**: Dynamically replaces placeholders (like `{theme_name}`) on mockup texts.
- **Automatic Asset Acquisition**: Installs high-quality typography (Google Fonts Outfit) at startup automatically.

---

## Directory Structure

```
etsy_mockup_creator/
├── templates/               # JSON configuration templates (Hero, Characters, etc.)
├── src/
│   ├── image_loader.py      # Category-based local PNG crawler
│   ├── template_loader.py   # Loader & validator for JSON schemas
│   ├── effects.py           # Scaling, rotations, outlines, and soft drop shadows
│   ├── text_renderer.py     # Font rendering, multi-line wrapping, alignment, and anchors
│   ├── renderer.py          # Layer composition and canvas creation
│   ├── generator.py         # Batch generator orchestrator
│   └── main.py              # CLI Entrypoint
├── assets/
│   └── fonts/               # Auto-downloaded Outfit Google Fonts
└── requirements.txt
```

---

## Requirements

Install requirements:
```bash
pip install -r requirements.txt
```

---

## How to Run

Generate mockups by providing the path to a categorized theme folder and a target output directory:

```bash
python -m src.main --theme path/to/Theme_Folder --output path/to/output_directory
```

### Folder Structure of Input Theme
The input directory must have subfolders representing image categories (e.g. `character`, `combo`, `prop`, `pattern`, `scene`):

```
Theme_Folder/
├── character/
│   ├── character_001.png
│   └── character_002.png
├── combo/
│   └── combo_001.png
├── prop/
│   ├── prop_001.png
│   └── prop_002.png
├── pattern/
│   └── pattern_001.png
└── scene/
    └── scene_001.png
```

---

## Adding Custom Templates

To add a new mockup design to your pipeline:
1. Create a new `.json` file inside the `templates/` folder.
2. Define the canvas size, background (gradient, color, or image), and elements in order of rendering.

Example layout element:
```json
{
  "type": "image",
  "source": {
    "category": "character",
    "index": 0
  },
  "x": 1000,
  "y": 950,
  "width": 800,
  "height": 800,
  "rotation": -3,
  "anchor": "center",
  "effects": {
    "outline": {
      "color": "#FFFFFF",
      "width": 15
    },
    "shadow": {
      "color": "#0000002A",
      "offset": [15, 20],
      "blur": 25
    }
  }
}
```
