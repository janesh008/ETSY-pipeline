# Feature Specification: Left Sidebar (Advanced Folder Navigation & Image Gallery)

This specification outlines the design, UI flow, and technical implementation details for the left sidebar image gallery and navigation system.

---

## 1. Feature Overview

The left sidebar serves as the asset explorer. Users can select a master theme folder, navigate through its sub-folders (like `character`, `prop`, etc.), and view images as thumbnails. This folder structure maps directly to the categories used in the template elements JSON.

---

## 2. User Experience & Interface Design

### UI Layout Wireframe
```
+───────────────────────────────────────────────────────────+
| [ Select Master Folder Button ]                           |
+───────────────────────────────────────────────────────────+
| Breadcrumbs: Master / Theme_Folder / [character]          |
| [ < Back Button ]                                         |
+───────────────────────────────────────────────────────────+
| Folder List (if inside parent):                           |
|  📁 character/ (12 images)                                |
|  📁 prop/ (6 images)                                      |
|  📁 combo/ (3 images)                                     |
+───────────────────────────────────────────────────────────+
| Image Thumbnails Gallery (if inside sub-folder):          |
|  +───────────+  +───────────+  +───────────+              |
|  |           |  |           |  |           |              |
|  |  [Image]  |  |  [Image]  |  |  [Image]  |              |
|  |           |  |           |  |           |              |
|  |  char_01  |  |  char_02  |  |  char_03  |              |
|  +───────────+  +───────────+  +───────────+              |
|  +───────────+  +───────────+  +───────────+              |
|  |           |  |           |  |           |              |
|  |  [Image]  |  |  [Image]  |  |  [Image]  |              |
|  |           |  |           |  |           |              |
|  |  char_04  |  |  char_05  |  |  char_06  |              |
|  +───────────+  +───────────+  +───────────+              |
+───────────────────────────────────────────────────────────+
```

### UX Flow
1. **Initial State**: The sidebar prompts the user to select a folder: `[ Select Master Folder ]`.
2. **Master Selected**: 
   - A native directory picker opens.
   - Once selected, the sidebar lists all top-level subfolders (e.g., `character`, `prop`, `pattern`) with folder icons, names, and image counts.
3. **Folder Navigation**:
   - Double-clicking or clicking a subfolder enters it.
   - The UI displays a breadcrumb trail showing the current path (e.g., `Master > pooh_gender_reveal > character`).
   - A `[ < Back ]` button appears to return to the parent directory.
4. **Image Display**:
   - Inside a subfolder, a grid of square image thumbnails (e.g., 90x90 pixels) renders.
   - Hovering over a thumbnail shows the filename and dimensions.
   - The panel is scrollable vertically.

---

## 3. Technical Implementation Details

### API endpoints (Local Python Backend)
To serve assets to the web interface, the local Python backend must expose the following REST endpoints:

#### 1. Select Master Directory
* **Endpoint**: `/api/select-master`
* **Method**: `POST`
* **Response**:
  ```json
  {
    "master_path": "d:/Janesh/etsy mockup creator/pooh_gender_reveal",
    "subfolders": [
      { "name": "character", "path": "character", "image_count": 12 },
      { "name": "prop", "path": "prop", "image_count": 6 },
      { "name": "combo", "path": "combo", "image_count": 3 }
    ]
  }
  ```

#### 2. Get Folder Contents
* **Endpoint**: `/api/folder-contents`
* **Method**: `GET`
* **Query Parameters**: `folder_relative_path=character`
* **Response**:
  ```json
  {
    "current_path": "character",
    "parent_path": "",
    "images": [
      { "name": "character_001.png", "url": "/api/image/character/character_001.png" },
      { "name": "character_002.png", "url": "/api/image/character/character_002.png" }
    ]
  }
  ```

#### 3. Serve Image Asset
* **Endpoint**: `/api/image/<path:path>`
* **Method**: `GET`
* **Description**: Returns the raw PNG binary data with correct MIME headers (`image/png`) to render in the browser.

---

## 4. Frontend State Management

The frontend uses a state object to manage folder traversal:

```javascript
const sidebarState = {
  masterPath: null,         // Absolute path to the master folder
  currentPath: "",          // Subfolder path relative to master folder (e.g., "character")
  history: [],              // Stack of visited paths for backtracking
  subfolders: [],           // List of subfolders in master
  currentImages: []         // List of images in the open folder
};
```

---

## 5. Performance Optimizations

1. **Lazy Loading**: If a folder contains hundreds of PNG assets, thumbnails should be lazy-loaded using an `IntersectionObserver` or the browser-native `loading="lazy"` attribute.
2. **Backend Image Resizing**: To prevent loading 20MB raw PNG files for 90x90 pixel thumbnails, the backend endpoint `/api/image` should support a `?size=150` query parameter to resize images on-the-fly and return compressed cacheable web-safe versions.
