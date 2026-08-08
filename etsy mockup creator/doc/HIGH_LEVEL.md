# 🎨 Etsy Mockup Creator — High Level Overview

Welcome to the **Etsy Mockup Creator** system! This document provides a friendly, non-technical high-level overview of how our mockup engine turns raw transparent clipart graphics into studio-quality Etsy listing images.

---

## 💡 What is the Etsy Mockup Creator?

The Etsy Mockup Creator is an automated engine that takes arbitrary transparent PNG clipart graphics (e.g., characters, scenes, text graphics) and automatically builds two types of high-converting Etsy listing mockups:

1. **Standard Hero & Grid Mockups (2000×2000px):**
   - High-impact composite graphic listing covers featuring title banners, multi-item grids (15–25 clipart items), badge overlays, and theme titles.
   - Uses `no_bg/` (700px) clipart images for fast, low-memory grid composition.

2. **Photorealistic Lifestyle Mockups (3000×3000px / 4000×4000px):**
   - Real-life model photos of T-shirts, Mugs, Pillows, and Wall Art Frames.
   - Uses `upscaled/` (4K 4096px) clipart images with true RGBA alpha blending, perspective warping, and fabric wrinkle/shadow overlays.
   - Automatically selects matching surface colors based on clipart visual tone.

---

## 🏗️ Folder Architecture at a Glance

Here is how the `etsy mockup creator` project is organized:

```
etsy mockup creator/
├── doc/                             <-- 📖 CENTRAL DOCUMENTATION CENTER
│   ├── HIGH_LEVEL.md               <-- (This file) Non-technical scope & overview
│   ├── SKILL.md                    <-- Coding standards, Gotchas, and design rules
│   ├── DETAILED.md                 <-- Detailed module-by-module technical specs
│   └── SHOP_AND_TEMPLATE_GUIDE.md  <-- Step-by-step guide for adding shops & templates
│
├── rendering/                       <-- ⚙️ MULTI-SHOP BUSINESS LOGIC
│   ├── shops/                      <-- Shop-specific templates & shop_config.yaml
│   ├── lifestyle_products/         <-- Photo templates (blank, mask, shadow, config)
│   ├── plugins/                    <-- Orchestrator, HeroPlugin, LifestyleOrchestrator
│   └── compatibility/              <-- Visual analyzer, bucket index, classifier
│
├── src/                             <-- 🛠️ CORE CANVAS & GRAPHICS ENGINE
│   ├── main.py                     <-- CLI Command Entry Point
│   ├── generator.py                <-- Batch generator orchestrator
│   ├── renderer.py                 <-- PIL canvas layer composition engine
│   ├── effects.py                  <-- Drop shadows, outline borders, rotations
│   ├── text_renderer.py            <-- Google Fonts typography & text wrapping
│   └── image_loader.py             <-- Local clipart category crawler
│
├── templates/                       <-- 📄 STANDARD JSON TEMPLATES
│   └── *.json                      <-- Grid & cover layouts with visual metadata
│
└── web_editor/                      <-- 🌐 WEB EDITOR UI & PREVIEW SERVER
    ├── server.py                   <-- Flask REST API backend
    ├── index.html                  <-- Visual drag-and-drop template editor UI
    └── static/                     <-- Web UI styles and JS scripts
```

---

## 🔄 Business Logic & Data Flow

```
                      Arbitrary Clipart PNGs
                                │
          ┌─────────────────────┴─────────────────────┐
          ▼                                           ▼
 Standard Hero Mockups                      Lifestyle Photo Mockups
(Generator + Renderer)                     (LifestyleOrchestrator)
          │                                           │
  - Grid Collages (700px)                    - Character Image Sampling
  - Text Wrapping                            - Visual Theme Classification
  - Soft Drop Shadows                        - O(1) Surface Bucket Lookup
  - Outline Borders                          - 4K OpenCV Perspective Warp
          │                                  - Fabric Wrinkle Shadow Multiply
          ▼                                           ▼
 High-Quality JPEGs (Quality 93)            High-Quality JPEGs (Quality 93)
 (800 KB – 1.2 MB file size)               (1.2 MB – 1.8 MB file size)
```

---

## 🚀 Key Non-Technical Highlights

1. **Zero Canva Manual Work:** Everything is 100% automated from CLI or API.
2. **Fast Etsy Publishing:** Exports JPEG Quality 93 images (1.2 MB – 1.8 MB) so listing uploads take seconds instead of minutes.
3. **Smart Matching:** Clipart artwork automatically finds compatible shirt/mug surface colors without manual intervention.
4. **No Code Required to Add Content:** Non-technical users can add new shops, JSON templates, or lifestyle photo surfaces simply by adding files and running helper scripts.
