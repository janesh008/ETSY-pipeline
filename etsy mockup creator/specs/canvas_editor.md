# Feature Specification: Canvas Image Editing (Resizing & Cropping)

This specification outlines the UI design, mechanics, and math equations for crop tools and active boundary-resize handlers for image elements.

---

## 1. Feature Overview

Once an image layer exists on the canvas, the user can modify its dimensions directly:
1. **Dynamic Resizing**: Corner and edge handles to scale and stretch the image layer.
2. **Interactive Cropping**: A visual overlay to crop transparent/empty boundaries or isolate a portion of the image.

---

## 2. User Experience & Interface Design

### Visual Resize Handles
When an image element is selected, 8 handle boxes appear:
- 4 Corner handles: maintains aspect ratio during scaling (default)
- 4 Edge handles: stretches the image horizontally or vertically (free scale)

```
        (Top Edge)
  [■]───────[■]───────[■] (Top Right)
   │                   │
   │                   │
  [■]     [Image]     [■] (Right Edge)
   │                   │
   │                   │
  [■]───────[■]───────[■]
(Bottom Left)
```

### Visual Cropping Overlay
Double-clicking an image or clicking the "Crop" button enters **Crop Mode**:
- The canvas turns semi-transparent dark, except for the selected image.
- Thick black crop brackets appear on the corners and edges of the image.
- Dragging these brackets restricts the visibility box (crop rectangle) of the image.
- Double-clicking outside or pressing `Enter` confirms the crop; `Esc` cancels it.

```
       (Crop Bracket)
  [┌]─────────────────[┐]
   │                   │
   │  Visible Region   │
   │                   │
  [└]─────────────────[┘]
```

---

## 3. Technical Implementation Details

### Resize Handler Mechanics
As the user drags a handle, the element updates in real-time:
* **Top-Left Handle**: Modifies both position (`x`, `y`) and size (`width`, `height`).
* **Bottom-Right Handle**: Modifies size (`width`, `height`) while keeping the top-left position anchored.
* **Proportional Scaling**: If dragging a corner, the aspect ratio is preserved:
  $$\text{New Height} = \text{New Width} \times \text{Aspect Ratio}$$

### Cropping Implementation
In the JSON schema, the template stores crop coordinates relative to the image:
```json
{
  "type": "image",
  "source": { "category": "character", "index": 0 },
  "x": 400,
  "y": 600,
  "width": 250,
  "height": 250,
  "crop": {
    "x": 50,    // pixel offset from original left edge
    "y": 20,    // pixel offset from original top edge
    "width": 150,
    "height": 180
  }
}
```

#### Canvas Rendering with Crop (Front-End)
When rendering the element on the canvas, the canvas engine draws a sub-rectangle of the source image:
```javascript
// HTML5 Canvas Context Drawing
ctx.drawImage(
  sourceImage,
  crop.x, crop.y, crop.width, crop.height, // Source coordinates
  drawX, drawY, drawWidth, drawHeight      // Canvas destination coordinates
);
```

#### Mockup Generator Integration (Python Backend)
The Pillow library in Python supports crops via the `.crop()` method:
```python
# During layer rendering in src/renderer.py
if "crop" in element:
    crop_cfg = element["crop"]
    cx = crop_cfg.get("x", 0)
    cy = crop_cfg.get("y", 0)
    cw = crop_cfg.get("width", elem_img.width)
    ch = crop_cfg.get("height", elem_img.height)
    # Crop bounds: (left, upper, right, lower)
    elem_img = elem_img.crop((cx, cy, cx + cw, cy + ch))
```

---

## 4. Undo and Redo Support

Every drag-to-resize release or crop confirmation pushes the complete state to the Undo stack to support revert capabilities (`Ctrl+Z`).
