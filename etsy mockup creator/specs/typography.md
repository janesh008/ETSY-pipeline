# Feature Specification: Typography & Fonts (Canva Font Library)

This specification defines the text addition tool, font selection library, and real-time font loading system for designing high-end textual content on the mockup templates.

---

## 1. Feature Overview

To produce premium, professional designs directly in the editor, users need a wide selection of modern fonts. The editor will provide a "Canva-like" dropdown font selector, dynamically downloading Google Fonts to style elements on the fly.

---

## 2. User Experience & Interface Design

### Font & Style Control Bar
When a text element is selected, the properties panel exposes rich layout and formatting controls:

```
Font Options
+─────────────────────────────────────────+
| Font:   [ Outfit-Bold               [▼] | <- Searchable list
| Size:   [ 90 px ]  [ - ] [ + ]          |
| Color:  [ #7A4B26 ] [■ Swatch]          |
| Align:  [ ≡ Left ] [ ≡ Center ] [ ≡ Right] |
| MaxW:   [ 1200 px ]                     |
| Letter Spacing: [ 1.2 ]                 |
+─────────────────────────────────────────+
```

### Font Library Explorer Panel
Users can browse fonts categorized by style:
- **Serif**: Playfair Display, Merriweather, Lora
- **Sans-Serif**: Inter, Roboto, Outfit, Montserrat, Open Sans
- **Display / Decorative**: Pacifico, Lobster, Cinzel, Bebas Neue
- **Handwritten**: Caveat, Sacremento, Dancing Script

---

## 3. Technical Implementation Details

### Dynamic Web Font Loading (Frontend)
To render text in the browser using custom fonts, the web editor dynamically loads font links via CSS:
```javascript
function loadGoogleFont(fontFamilyName) {
  const fontId = `gfont-${fontFamilyName.replace(/\s+/g, '-').toLowerCase()}`;
  
  // Prevent double loading
  if (document.getElementById(fontId)) return;
  
  const link = document.createElement('link');
  link.id = fontId;
  link.rel = 'stylesheet';
  link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(fontFamilyName)}:wght@400;700&display=swap`;
  
  document.head.appendChild(link);
}
```

### Font Acquisition & Local Caching (Python Backend)
To render the final high-resolution mockups inside Pillow, the Python server needs to download the raw `.ttf` file of the selected font:

#### Dynamic Download Endpoint
* **Endpoint**: `/api/fonts/download`
* **Method**: `POST`
* **Payload**:
  ```json
  { "font_family": "Montserrat" }
  ```
* **Python Behavior (in backend server)**:
  1. Searches the local `assets/fonts/` directory for `Montserrat-Regular.ttf` or `Montserrat-Bold.ttf`.
  2. If missing, requests Google Fonts Developer API details to obtain the direct `.ttf` source URL.
  3. Downloads the font file and saves it locally.
  4. Returns a success confirmation, allowing the backend generator to utilize the font immediately.

---

## 4. Extended Schema

To support custom fonts and advanced typography, the template elements format is expanded:

```json
{
  "type": "text",
  "content": "pooh gender reveal PNGS",
  "x": 1000,
  "y": 830,
  "font_family": "Montserrat-Bold",  // Downloaded and cached
  "font_size": 92,
  "color": "#7A4B26",
  "anchor": "center",
  "align": "center",
  "letter_spacing": 1.2,              // Additional feature: char-spacing
  "line_height": 1.5                  // Additional feature: multi-line spacing
}
```

---

## 5. Google Fonts Fallbacks

If a font download fails (e.g. offline mode), the frontend drops back to local web-safe fonts (`Arial`, `sans-serif`), and the backend system drops back to the local `Outfit-Regular.ttf` or system fallback to prevent runtime crashes.
