# Feature Specification: Drag-and-Drop Functionality

This specification defines the interactive behavior and technical integration of dragging images from the sidebar gallery and dropping them onto the canvas editor.

---

## 1. Feature Overview

Users should be able to click on any image preview thumbnail in the left sidebar, drag it over the central canvas area, and release it. This action creates a new image layer (element) in the template configuration.

---

## 2. User Experience & Drag-Drop Interaction

### UI Visual States

```
+───────────────────+    +─────────────────────────────────────────+
| Sidebar Gallery   |    | Workspace Canvas (2000x2000 scaled)      |
|                   |    |                                         |
|  +───────────+    |    |      +───────────────────────────+      |
|  | [Thumbnail]────┼────┼─────>|  [ Dotted Highlight Box ] |      |
|  +───────────+    |    |      |  "Drop Here to Add"       |      |
|    (Dragged       |    |      |  x: 1050, y: 840          |      |
|     Ghost)        |    |      +───────────────────────────+      |
+───────────────────+    +─────────────────────────────────────────+
```

### Drag & Drop States:
1. **Drag Start**:
   - The user clicks and drags a thumbnail.
   - The thumbnail opacity decreases, and a semi-transparent "ghost copy" of the image follows the mouse cursor.
2. **Drag Enter Canvas**:
   - As the cursor enters the canvas, a dotted drop-zone border highlights the canvas boundaries.
   - The canvas displays a tooltip showing the target coordinates in the canvas space (e.g. `X: 1050, Y: 840`).
3. **Drop Action**:
   - Releasing the mouse button drops the image onto the canvas.
   - The drag ghost fades out.
   - A new image layer is added to the canvas at the coordinates where the mouse was released.
   - The newly added image is automatically selected, showing resizing handles.

---

## 3. Technical Implementation Details

Using standard web technologies (HTML5 Canvas + Drag and Drop API), the interaction is implemented via event listeners:

### HTML5 Drag Events:
* **Source Element (Sidebar Image)**:
  - `draggable="true"` attribute enabled.
  - `dragstart` event: Serializes the image category and index data inside the dataTransfer object.
    ```javascript
    event.dataTransfer.setData("application/json", JSON.stringify({
      category: "character",
      index: 2,
      aspect_ratio: 1.0  // Preserved for initial scaling
    }));
    ```
* **Target Element (Workspace Canvas)**:
  - `dragover` event: Calls `event.preventDefault()` to allow dropping. Tracks cursor screen positions to calculate active coordinates.
  - `dragleave` event: Removes target highlighting.
  - `drop` event: Reads the dataTransfer package, converts the client window drops coordinates into the 2000x2000 template coordinate space, and inserts a new element.

---

## 4. Coordinate Conversion Math

To place the dropped element at the correct location, the UI must translate screen pixels to the logical coordinate space of the template:

$$X_{logical} = \frac{X_{client} - OffsetX}{Scale}$$

$$Y_{logical} = \frac{Y_{client} - OffsetY}{Scale}$$

Where:
* $X_{client}, Y_{client}$ are the drop cursor coordinates relative to the canvas canvas container.
* $OffsetX, OffsetY$ is the viewport panning offset.
* $Scale$ is the current viewport zoom multiplier (e.g., `0.40`).

---

## 5. State Integration

On drop, the UI triggers a state update:

```javascript
function onImageDrop(logicalX, logicalY, imageMetadata) {
  const newElement = {
    type: "image",
    source: {
      category: imageMetadata.category,  // e.g. "character"
      index: imageMetadata.index          // e.g. 2
    },
    x: Math.round(logicalX),
    y: Math.round(logicalY),
    width: 300,  // default size
    height: Math.round(300 / imageMetadata.aspect_ratio),
    anchor: "center"
  };
  
  // Update state array
  appState.template.elements.push(newElement);
  appState.selectedElementIndex = appState.template.elements.length - 1;
  
  renderCanvas();
  renderPropertiesPanel();
  saveToUndoStack();
}
```
