/* ─────────────────────────────────────────────────────────────────────────────
 * Automated Etsy Mockup Generator — Visual Canvas Editor Frontend Application
 * ──────────────────────────────────────────────────────────────────────────── */

// Global State Object
const state = {
  template: {
    name: "New Template",
    canvas_size: [2000, 2000],
    background: { type: "solid", color: "#FFFFFF" },
    elements: []
  },
  selectedFilename: "",
  selectedElementIndex: null,
  scale: 0.35,              // Visual canvas zoom scale relative to 2000px
  offsetX: 0,
  offsetY: 0,
  
  // Master folder configuration
  masterPath: null,
  currentCategory: "",      // relative category path explorer
  subfolders: [],
  currentImages: [],
  
  // Image cache mapping absolute URL to loaded HTML Image Object
  imageCache: {},
  
  // Drag bookkeeping
  dragState: {
    active: false,
    elementIndex: null,
    startX: 0,
    startY: 0,
    origX: 0,
    origY: 0,
    mode: "move",          // "move" or "resize" or "crop"
    handle: ""             // tl, tm, tr, ml, mr, bl, bm, br
  },
  
  // Cropping State
  cropState: {
    active: false,
    originalCrop: null,    // backup in case of cancel
  },
  
  // Undo/Redo tracking
  undoStack: [],
  redoStack: []
};

// Constant category color borders
const CATEGORY_COLORS = {
  character:    "#3b82f6",
  prop:         "#ef4444",
  combo:        "#10b981",
  pattern:      "#f59e0b",
  scene:        "#8b5cf6",
  subcharacter: "#06b6d4"
};

function getCategoryColor(category) {
  if (!category) return "#94a3b8";
  const cat = category.toLowerCase();
  if (CATEGORY_COLORS[cat]) return CATEGORY_COLORS[cat];
  
  if (cat.startsWith("sub_character") || cat.startsWith("subcharacter")) return CATEGORY_COLORS.subcharacter;
  if (cat.startsWith("character_combo") || cat.startsWith("combo")) return CATEGORY_COLORS.combo;
  if (cat.startsWith("pattern")) return CATEGORY_COLORS.pattern;
  if (cat.startsWith("prop")) return CATEGORY_COLORS.prop;
  if (cat.startsWith("scene")) return CATEGORY_COLORS.scene;
  
  return "#94a3b8";
}

// ─────────────────────────────────────────────────────────────────────────────
// DOM Node Cache
// ────────────────────────────────────────────────────────────────────────────

const el = {
  templateSelect:   document.getElementById("template-select"),
  templateName:     document.getElementById("template-name"),
  btnBatchRun:      document.getElementById("btn-batch-run"),
  btnSelectFolder:  document.getElementById("btn-select-folder"),
  btnSaveTemplate:  document.getElementById("btn-save-template"),
  btnGenerate:      document.getElementById("btn-generate"),
  
  // Sidebar Left Explorer
  breadcrumbs:       document.getElementById("gallery-breadcrumbs"),
  btnGalleryBack:    document.getElementById("btn-gallery-back"),
  subfoldersList:    document.getElementById("subfolders-list"),
  thumbnailsGrid:    document.getElementById("image-thumbnails-grid"),
  
  // Canvas Viewport Controls
  canvasContainer:  document.getElementById("canvas-container-outer"),
  canvasWrapper:    document.getElementById("canvas-wrapper"),
  canvas:           document.getElementById("editor-canvas"),
  overlay:          document.getElementById("canvas-overlay"),
  selectionBox:     document.getElementById("selection-box"),
  
  zoomIn:           document.getElementById("btn-zoom-in"),
  zoomOut:          document.getElementById("btn-zoom-out"),
  zoomFit:          document.getElementById("btn-zoom-fit"),
  zoomLbl:          document.getElementById("zoom-lbl"),
  chkGrid:          document.getElementById("chk-grid"),
  
  btnAddImage:      document.getElementById("btn-add-image"),
  btnAddText:       document.getElementById("btn-add-text"),
  btnMoveUp:        document.getElementById("btn-move-up"),
  btnMoveDown:      document.getElementById("btn-move-down"),
  btnDuplicate:     document.getElementById("btn-duplicate"),
  btnDelete:        document.getElementById("btn-delete"),
  
  // Right Sidebar Properties panels
  propNoSelection:  document.getElementById("prop-no-selection"),
  propImagePanel:   document.getElementById("prop-image-panel"),
  propTextPanel:    document.getElementById("prop-text-panel"),
  
  // Base canvas settings
  canvasFile:       document.getElementById("prop-canvas-file"),
  canvasW:          document.getElementById("prop-canvas-w"),
  canvasH:          document.getElementById("prop-canvas-h"),
  bgType:           document.getElementById("prop-bg-type"),
  bgSolidCtrls:     document.getElementById("bg-solid-controls"),
  bgColor:          document.getElementById("prop-bg-color"),
  bgColorHex:       document.getElementById("prop-bg-color-hex"),
  bgGradCtrls:      document.getElementById("bg-gradient-controls"),
  bgGradStart:      document.getElementById("prop-bg-grad-start"),
  bgGradEnd:        document.getElementById("prop-bg-grad-end"),
  
  // Image properties settings
  imgCategory:      document.getElementById("prop-img-category"),
  imgIndex:         document.getElementById("prop-img-index"),
  imgX:             document.getElementById("prop-img-x"),
  imgY:             document.getElementById("prop-img-y"),
  imgW:             document.getElementById("prop-img-w"),
  imgH:             document.getElementById("prop-img-h"),
  imgRot:           document.getElementById("prop-img-rot"),
  imgAnchor:        document.getElementById("prop-img-anchor"),
  
  btnTriggerCrop:   document.getElementById("btn-trigger-crop"),
  cropStatusBox:    document.getElementById("crop-active-indicator"),
  btnCropConfirm:   document.getElementById("btn-crop-confirm"),
  btnCropCancel:    document.getElementById("btn-crop-cancel"),
  
  chkOutline:       document.getElementById("chk-effect-outline"),
  outlineSub:       document.getElementById("outline-settings-sub"),
  olWidth:          document.getElementById("prop-ol-width"),
  olColor:          document.getElementById("prop-ol-color"),
  
  chkShadow:        document.getElementById("chk-effect-shadow"),
  shadowSub:        document.getElementById("shadow-settings-sub"),
  shBlur:           document.getElementById("prop-sh-blur"),
  shColor:          document.getElementById("prop-sh-color"),
  shDx:             document.getElementById("prop-sh-dx"),
  shDy:             document.getElementById("prop-sh-dy"),
  
  // Text properties settings
  textContent:      document.getElementById("prop-text-content"),
  fontSearch:       document.getElementById("font-search"),
  textFont:         document.getElementById("prop-text-font"),
  textSize:         document.getElementById("prop-text-size"),
  textColor:        document.getElementById("prop-text-color"),
  textColorHex:     document.getElementById("prop-text-color-hex"),
  textAlign:        document.getElementById("prop-text-align"),
  textAnchor:       document.getElementById("prop-text-anchor"),
  textX:            document.getElementById("prop-text-x"),
  textY:            document.getElementById("prop-text-y"),
  textMaxW:         document.getElementById("prop-text-maxw"),
  
  // Preview Output Modal
  modalPreview:      document.getElementById("modal-preview"),
  modalPreviewClose: document.getElementById("modal-preview-close"),
  modalPreviewOk:    document.getElementById("modal-preview-ok"),
  previewImg:        document.getElementById("preview-output-img"),
  previewPath:       document.getElementById("preview-path")
};

// 2D Drawing Context
const ctx = el.canvas.getContext("2d");

// ─────────────────────────────────────────────────────────────────────────────
// Initialization
// ────────────────────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  loadLocalFonts();  // Register all asset fonts as @font-face for canvas rendering
  setupEventListeners();
  loadTemplateList();
  fitCanvasToViewport();
  render();
});

// ─────────────────────────────────────────────────────────────────────────────
// Event Bindings setup
// ────────────────────────────────────────────────────────────────────────────

function setupEventListeners() {
  // Folder explorer load
  el.btnBatchRun.addEventListener("click", runBatchGeneration);
  el.btnSelectFolder.addEventListener("click", selectMasterFolder);
  el.btnGalleryBack.addEventListener("click", navigateToMaster);
  
  // Template Selectors
  el.templateSelect.addEventListener("change", (e) => {
    if (e.target.value) {
      loadTemplate(e.target.value);
    }
  });
  
  el.templateName.addEventListener("input", (e) => {
    state.template.name = e.target.value;
  });
  
  el.btnSaveTemplate.addEventListener("click", saveActiveTemplate);
  el.btnGenerate.addEventListener("click", generateMockupPreview);
  
  // Toolbar additions/modifications
  el.btnAddImage.addEventListener("click", addImageElement);
  el.btnAddText.addEventListener("click", addTextElement);
  el.btnDelete.addEventListener("click", deleteSelectedElement);
  el.btnDuplicate.addEventListener("click", duplicateSelectedElement);
  el.btnMoveUp.addEventListener("click", () => moveLayer(1));
  el.btnMoveDown.addEventListener("click", () => moveLayer(-1));
  
  // View Zoom operations
  el.zoomIn.addEventListener("click", () => zoom(1.15));
  el.zoomOut.addEventListener("click", () => zoom(1 / 1.15));
  el.zoomFit.addEventListener("click", fitCanvasToViewport);
  el.chkGrid.addEventListener("change", render);
  
  // Handle dragging operations on viewport overlay
  el.overlay.addEventListener("mousedown", onCanvasMouseDown);
  window.addEventListener("mousemove", onCanvasMouseMove);
  window.addEventListener("mouseup", onCanvasMouseUp);
  
  // Drag and Drop sidebar events
  el.overlay.addEventListener("dragenter", (e) => {
    e.preventDefault();
    el.overlay.classList.add("drag-over");
  });
  
  el.overlay.addEventListener("dragover", (e) => {
    e.preventDefault();
  });
  
  el.overlay.addEventListener("dragleave", () => {
    el.overlay.classList.remove("drag-over");
  });
  
  el.overlay.addEventListener("drop", onCanvasDrop);
  
  // Properties panel integrations
  setupPropertyInputs();
  
  // Modal previews
  el.modalPreviewClose.addEventListener("click", () => el.modalPreview.classList.add("hidden"));
  el.modalPreviewOk.addEventListener("click", () => el.modalPreview.classList.add("hidden"));
}

// ─────────────────────────────────────────────────────────────────────────────
// Folder Navigation & API
// ────────────────────────────────────────────────────────────────────────────

async function selectMasterFolder() {
  const path = prompt("Enter the absolute path of your Theme Folder (e.g., D:/Janesh/etsy mockup creator/pooh_gender_reveal):", state.masterPath || "");
  if (!path) return;
  
  try {
    const res = await fetch("/api/select-master", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path })
    });
    const data = await res.json();
    
    if (data.error) {
      alert("Error selecting directory: " + data.error);
      return;
    }
    
    state.masterPath = data.master_path;
    state.subfolders = data.subfolders;
    
    // Clear image cache and rerender
    state.imageCache = {};
    navigateToMaster();
  } catch (err) {
    console.error("Failed to call select-master:", err);
  }
}

async function runBatchGeneration() {
  const path = prompt(
    "Enter the absolute path of your Main Clipart Folder containing multiple themes (e.g., D:/Janesh/Cliparts):",
    state.masterPath ? state.masterPath.substring(0, state.masterPath.lastIndexOf("/")) : ""
  );
  if (!path) return;
  
  const originalText = el.btnBatchRun.textContent;
  el.btnBatchRun.textContent = "⏳ Running...";
  el.btnBatchRun.disabled = true;
  
  try {
    const res = await fetch("/api/batch-generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ batch_dir: path })
    });
    const data = await res.json();
    
    if (data.error) {
      alert("Error in batch generation: " + data.error);
    } else {
      alert(`Success!\n\nProcessed themes:\n${data.processed_themes.map(t => "• " + t).join("\n")}`);
    }
  } catch (err) {
    alert("Network or Server error executing batch generation: " + err);
  } finally {
    el.btnBatchRun.textContent = originalText;
    el.btnBatchRun.disabled = false;
  }
}

function navigateToMaster() {
  state.currentCategory = "";
  el.btnGalleryBack.classList.add("hidden");
  el.thumbnailsGrid.classList.add("hidden");
  el.subfoldersList.classList.remove("hidden");
  
  el.breadcrumbs.innerHTML = `<span class="breadcrumb-item active">${state.masterPath ? state.masterPath.split("/").pop() : "Theme"}</span>`;
  
  // Render subfolder items
  el.subfoldersList.innerHTML = "";
  if (state.subfolders.length === 0) {
    el.subfoldersList.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📁</span>
        <p>No subfolders containing PNGs found inside the loaded master folder.</p>
      </div>`;
    return;
  }
  
  state.subfolders.forEach(sub => {
    const item = document.createElement("div");
    item.className = "folder-item";
    item.innerHTML = `
      <div class="folder-info">
        <span class="folder-icon">📁</span>
        <span class="folder-name">${sub.name}</span>
      </div>
      <span class="folder-count">${sub.image_count}</span>
    `;
    item.addEventListener("click", () => selectCategory(sub.path));
    el.subfoldersList.appendChild(item);
  });
}

async function selectCategory(catPath) {
  state.currentCategory = catPath;
  el.btnGalleryBack.classList.remove("hidden");
  el.subfoldersList.classList.add("hidden");
  el.thumbnailsGrid.classList.remove("hidden");
  
  // Breadcrumb update
  const masterName = state.masterPath.split("/").pop();
  el.breadcrumbs.innerHTML = `
    <span class="breadcrumb-item" onclick="navigateToMaster()">${masterName}</span>
    <span class="divider">/</span>
    <span class="breadcrumb-item active">${catPath}</span>
  `;
  
  el.thumbnailsGrid.innerHTML = `<div class="empty-state"><p>Loading image thumbnails...</p></div>`;
  
  try {
    const res = await fetch(`/api/folder-contents?folder_relative_path=${encodeURIComponent(catPath)}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      alert("Error loading folder contents: " + (errData.error || res.statusText));
      el.thumbnailsGrid.innerHTML = `<div class="empty-state"><p>Failed to load images.</p></div>`;
      return;
    }
    const data = await res.json();
    
    state.currentImages = data.images || [];
    renderThumbnails();
  } catch (err) {
    console.error("Failed load category:", err);
    el.thumbnailsGrid.innerHTML = `<div class="empty-state"><p>Failed to load images.</p></div>`;
  }
}

function renderThumbnails() {
  el.thumbnailsGrid.innerHTML = "";
  if (state.currentImages.length === 0) {
    el.thumbnailsGrid.innerHTML = `<div class="empty-state"><p>No PNG images inside this folder.</p></div>`;
    return;
  }
  
  state.currentImages.forEach((img, index) => {
    const card = document.createElement("div");
    card.className = "thumbnail-card";
    card.setAttribute("draggable", "true");
    
    // Lazy loaded image thumbnail (resized via server to 150px)
    const thumbUrl = `${img.url}&size=150`;
    card.innerHTML = `
      <img src="${thumbUrl}" alt="${img.name}" loading="lazy">
      <span class="thumbnail-label">${index}. ${img.name.replace(/_character_|_prop_|_combo_|_pattern_|_scene_/gi, " ")}</span>
    `;
    
    // HTML5 Drag Event Listeners
    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("application/json", JSON.stringify({
        category: state.currentCategory,
        index: index,
        src: img.url
      }));
      e.dataTransfer.effectAllowed = "copy";
    });
    
    el.thumbnailsGrid.appendChild(card);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Drag & Drop onto Canvas
// ────────────────────────────────────────────────────────────────────────────

function onCanvasDrop(e) {
  e.preventDefault();
  el.overlay.classList.remove("drag-over");
  
  try {
    const rawData = e.dataTransfer.getData("application/json");
    if (!rawData) return;
    
    const info = JSON.parse(rawData);
    
    // Fetch drop coordinates relative to canvas wrapper element
    const rect = el.canvasWrapper.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    // Scale client pixels back to 2000px coordinate space
    const logicalX = mouseX / state.scale;
    const logicalY = mouseY / state.scale;
    
    saveUndoState();
    
    const newElem = {
      type: "image",
      source: {
        category: info.category,
        index: info.index
      },
      x: Math.round(logicalX),
      y: Math.round(logicalY),
      width: 400,
      height: 400,
      rotation: 0,
      anchor: "center"
    };
    
    state.template.elements.push(newElem);
    state.selectedElementIndex = state.template.elements.length - 1;
    
    // Load and cache dropped image
    preloadImage(info.src).then(() => {
      render();
      updatePropertiesPanel();
    });
  } catch (err) {
    console.error("Drop error:", err);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Template Files API
// ────────────────────────────────────────────────────────────────────────────

async function loadTemplateList() {
  try {
    const res = await fetch("/api/templates");
    const templates = await res.json();
    
    el.templateSelect.innerHTML = `<option value="">-- Load Template --</option>`;
    templates.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.filename;
      opt.textContent = `${t.name} (${t.filename})`;
      el.templateSelect.appendChild(opt);
    });
  } catch (err) {
    console.error("Failed loading templates list:", err);
  }
}

async function loadTemplate(filename) {
  try {
    const res = await fetch(`/api/templates/${filename}`);
    const data = await res.json();
    
    state.template = data;
    state.selectedFilename = filename;
    state.selectedElementIndex = null;
    
    el.templateName.value = data.name || "Mockup Layout";
    el.canvasFile.value = filename;
    el.canvasW.value = data.canvas_size[0];
    el.canvasH.value = data.canvas_size[1];
    
    // Set background selectors
    const bg = data.background || { type: "solid", color: "#FFFFFF" };
    el.bgType.value = bg.type || "solid";
    el.bgColor.value = bg.color || "#FFFFFF";
    el.bgColorHex.value = bg.color || "#FFFFFF";
    el.bgGradStart.value = bg.color_start || "#FFFFFF";
    el.bgGradEnd.value = bg.color_end || "#CCCCCC";
    
    // Preload elements images
    await preloadAllTemplateImages();
    
    fitCanvasToViewport();
    render();
    updatePropertiesPanel();
  } catch (err) {
    alert("Error loading template: " + err);
  }
}

async function preloadAllTemplateImages() {
  const promises = [];
  state.template.elements.forEach(elem => {
    if (elem.type === "image" && elem.source && state.masterPath) {
      const srcPath = `${state.masterPath}/${elem.source.category}`;
      const url = `/api/image?path=${encodeURIComponent(srcPath)}&index=${elem.source.index}`;
      // In web app, templates don't store raw absolute paths, but our backend can serve them if category folder is known
      // We load based on category index endpoint:
      // Let's resolve the URL via serving by index or category:
      // We'll create a smart fallback url:
      const category = elem.source.category;
      const index = elem.source.index;
      const cachedUrl = `/api/image?category=${category}&index=${index}`;
      // For now, we resolve real image serving by indexing in backend
    }
  });
  await Promise.all(promises);
}

// Preloads image helper
function preloadImage(url) {
  if (state.imageCache[url]) return Promise.resolve(state.imageCache[url]);
  
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      state.imageCache[url] = img;
      resolve(img);
    };
    img.onerror = () => {
      // Create colored dummy image
      console.warn("Failed loading image asset:", url);
      resolve(null);
    };
    img.src = url;
  });
}

// Helper to get image element url based on local master path details
function getElementImageUrl(elem) {
  if (!state.masterPath || !elem.source) return null;
  const category = elem.source.category;
  const index = elem.source.index;
  
  // If we have loaded current category thumbnails, use that path
  if (state.currentCategory === category && state.currentImages[index % state.currentImages.length]) {
    return state.currentImages[index % state.currentImages.length].url;
  }
  
  // Fallback: request serving directly using category and index
  // We can query the backend which handles category mapping:
  // Let's call a directory check internally:
  return `/api/image?path=${encodeURIComponent(state.masterPath + "/" + category)}&index=${index}`;
}

async function saveActiveTemplate() {
  if (!state.selectedFilename) {
    const name = prompt("Enter a filename to save this template (e.g. custom.json):");
    if (!name) return;
    state.selectedFilename = name.endsWith(".json") ? name : name + ".json";
  }
  
  try {
    const res = await fetch(`/api/templates/${state.selectedFilename}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.template)
    });
    const result = await res.json();
    if (result.success) {
      alert("Template saved successfully!");
      loadTemplateList();
    } else {
      alert("Error saving: " + result.error);
    }
  } catch (err) {
    alert("Save request failed: " + err);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Canvas Zoom and Fit
// ────────────────────────────────────────────────────────────────────────────

function zoom(factor) {
  state.scale = Math.max(0.05, Math.min(2.5, state.scale * factor));
  updateZoomUI();
}

function fitCanvasToViewport() {
  const containerW = el.canvasContainer.clientWidth;
  const containerH = el.canvasContainer.clientHeight;
  const canvasW = state.template.canvas_size[0];
  const canvasH = state.template.canvas_size[1];
  
  const scaleX = (containerW - 60) / canvasW;
  const scaleY = (containerH - 60) / canvasH;
  
  state.scale = Math.min(scaleX, scaleY);
  updateZoomUI();
}

function updateZoomUI() {
  el.zoomLbl.textContent = `${Math.round(state.scale * 100)}%`;
  
  const cw = state.template.canvas_size[0];
  const ch = state.template.canvas_size[1];
  
  el.canvasWrapper.style.width = `${cw * state.scale}px`;
  el.canvasWrapper.style.height = `${ch * state.scale}px`;
  
  el.canvas.width = cw;
  el.canvas.height = ch;
  el.canvas.style.width = `${cw * state.scale}px`;
  el.canvas.style.height = `${ch * state.scale}px`;
  
  render();
}

// ─────────────────────────────────────────────────────────────────────────────
// Add & Delete Elements
// ────────────────────────────────────────────────────────────────────────────

function addImageElement() {
  saveUndoState();
  const cw = state.template.canvas_size[0];
  const ch = state.template.canvas_size[1];
  
  const newElem = {
    type: "image",
    source: {
      category: "character",
      index: 0
    },
    x: Math.round(cw / 2),
    y: Math.round(ch / 2),
    width: 400,
    height: 400,
    rotation: 0,
    anchor: "center"
  };
  
  state.template.elements.push(newElem);
  state.selectedElementIndex = state.template.elements.length - 1;
  
  render();
  updatePropertiesPanel();
}

function addTextElement() {
  saveUndoState();
  const cw = state.template.canvas_size[0];
  const ch = state.template.canvas_size[1];
  
  const newElem = {
    type: "text",
    content: "Double click to edit",
    x: Math.round(cw / 2),
    y: Math.round(ch / 2),
    font_family: "Outfit-Bold",
    font_size: 72,
    color: "#000000",
    anchor: "center",
    align: "center"
  };
  
  state.template.elements.push(newElem);
  state.selectedElementIndex = state.template.elements.length - 1;
  
  render();
  updatePropertiesPanel();
}

function deleteSelectedElement() {
  if (state.selectedElementIndex === null) return;
  saveUndoState();
  
  state.template.elements.splice(state.selectedElementIndex, 1);
  state.selectedElementIndex = null;
  
  render();
  updatePropertiesPanel();
}

function duplicateSelectedElement() {
  if (state.selectedElementIndex === null) return;
  saveUndoState();
  
  const source = state.template.elements[state.selectedElementIndex];
  const copy = JSON.parse(JSON.stringify(source));
  
  // Offset slightly
  copy.x += 30;
  copy.y += 30;
  
  state.template.elements.push(copy);
  state.selectedElementIndex = state.template.elements.length - 1;
  
  render();
  updatePropertiesPanel();
}

function moveLayer(dir) {
  if (state.selectedElementIndex === null) return;
  const idx = state.selectedElementIndex;
  const targetIdx = idx + dir;
  
  if (targetIdx < 0 || targetIdx >= state.template.elements.length) return;
  
  saveUndoState();
  const temp = state.template.elements[idx];
  state.template.elements[idx] = state.template.elements[targetIdx];
  state.template.elements[targetIdx] = temp;
  state.selectedElementIndex = targetIdx;
  
  render();
  updatePropertiesPanel();
}

// ─────────────────────────────────────────────────────────────────────────────
// Canvas Render Engine
// ────────────────────────────────────────────────────────────────────────────

function render() {
  ctx.clearRect(0, 0, el.canvas.width, el.canvas.height);
  
  // 1. Draw Canvas Background
  drawBackground();
  
  // 2. Draw Elements
  state.template.elements.forEach((elem, index) => {
    if (elem.type === "image") {
      drawElImage(elem, index === state.selectedElementIndex);
    } else if (elem.type === "text") {
      drawElText(elem, index === state.selectedElementIndex);
    }
  });
  
  // 3. Draw Grid lines if checked
  if (el.chkGrid.checked) {
    drawGridOverlay();
  }
  
  // 4. Update dynamic selection handles bounds
  updateOverlayBounds();
}

function drawBackground() {
  const w = state.template.canvas_size[0];
  const h = state.template.canvas_size[1];
  const bg = state.template.background || { type: "solid", color: "#FFFFFF" };
  
  if (bg.type === "gradient") {
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, bg.color_start || "#FFFFFF");
    grad.addColorStop(1, bg.color_end || "#CCCCCC");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  } else {
    ctx.fillStyle = bg.color || "#FFFFFF";
    ctx.fillRect(0, 0, w, h);
  }
}

function drawElImage(elem, isSelected) {
  const category = elem.source.category;
  const index = elem.source.index;
  
  // Determine if image loaded in cache
  const cacheKey = `${category}_${index}`;
  
  // Formulate serving URL
  let url = "";
  if (state.masterPath) {
    // If master folder is loaded, query via category and index
    url = `/api/image?category=${encodeURIComponent(category)}&index=${index}`;
  }
  
  // Retrieve image
  let imgObj = state.imageCache[cacheKey];
  
  if (!imgObj && url) {
    // Background load
    preloadImage(url).then(loadedImg => {
      if (loadedImg) {
        state.imageCache[cacheKey] = loadedImg;
        render(); // trigger canvas repaint once loaded
      }
    });
  }
  
  const w = elem.width || 400;
  const h = elem.height || 400;
  
  // Compute top-left drawing coords based on Anchor settings
  let drawX = elem.x;
  let drawY = elem.y;
  
  if (elem.anchor === "center") {
    drawX -= w / 2;
    drawY -= h / 2;
  }
  
  ctx.save();
  
  // Apply rotation
  if (elem.rotation) {
    // Move pivot point to center
    const cx = drawX + w / 2;
    const cy = drawY + h / 2;
    ctx.translate(cx, cy);
    ctx.rotate((elem.rotation * Math.PI) / 180);
    ctx.translate(-cx, -cy);
  }
  
  if (imgObj) {
    // If image has crop properties defined
    if (elem.crop) {
      const c = elem.crop;
      ctx.drawImage(
        imgObj,
        c.x, c.y, c.width, c.height, // Source crop rectangle
        drawX, drawY, w, h           // Destination canvas rectangle
      );
    } else {
      ctx.drawImage(imgObj, drawX, drawY, w, h);
    }
  } else {
    // Visual placeholder box
    ctx.fillStyle = getCategoryColor(category);
    ctx.globalAlpha = 0.6;
    ctx.fillRect(drawX, drawY, w, h);
    ctx.globalAlpha = 1.0;
    
    // Label details
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 4;
    ctx.font = "bold 24px Outfit";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    
    const label = `${category}[${index}]`;
    ctx.strokeText(label, drawX + w / 2, drawY + h / 2);
    ctx.fillText(label, drawX + w / 2, drawY + h / 2);
  }
  
  // Visual bounding thin dotted box for images even if unselected
  if (isSelected) {
    ctx.strokeStyle = "#6366f1";
    ctx.lineWidth = 3;
    ctx.setLineDash([8, 4]);
    ctx.strokeRect(drawX, drawY, w, h);
  }
  
  ctx.restore();
}

function getInterpolatedText(content) {
  if (!content) return "";
  
  const bundleCount = state.subfolders.length > 0 
    ? state.subfolders.reduce((sum, sub) => sum + sub.image_count, 0)
    : 145; // Default fallback placeholder if no theme loaded
    
  const themeName = state.masterPath 
    ? state.masterPath.split("/").pop().replace(/_/g, " ") 
    : "Theme Name";
  const themeNameTitle = themeName.replace(/\b\w/g, c => c.toUpperCase());
  const themeNameUpper = themeName.toUpperCase();
  
  let result = content;
  result = result.replace(/{theme_name_title}/g, themeNameTitle);
  result = result.replace(/{theme_name_upper}/g, themeNameUpper);
  result = result.replace(/{theme_name}/g, themeName);
  result = result.replace(/{bundle_count}/g, bundleCount);
  return result;
}

function drawElText(elem, isSelected) {
  ctx.save();
  
  const text = elem.content || "Text Layer";
  const content = getInterpolatedText(text);
  
  const size = elem.font_size || 48;
  const font = elem.font_family || "Outfit-Regular";
  const color = elem.color || "#000000";
  
  // Format font string for HTML5 Canvas
  let weight = "";
  if (font.toLowerCase().includes("bold")) weight = "bold ";
  ctx.font = `${weight}${size}px "${font}", Arial`;
  
  ctx.fillStyle = color;
  ctx.textAlign = elem.align || "center";
  ctx.textBaseline = "alphabetic";
  
  // Dynamic line wrapping if max_width is specified
  const maxW = elem.max_width || 0;
  let lines = [content];
  
  if (maxW > 0) {
    lines = wrapTextLines(content, ctx, maxW);
  }
  
  // Compute height bounds
  const lineHeight = size * 1.15;
  const totalH = lines.length * lineHeight;
  
  let startY = elem.y;
  
  // Adjust starting Y relative to alignment anchors
  if (elem.anchor === "center") {
    // Shift vertically to center multi-line stack
    startY = elem.y - totalH / 2 + size * 0.8;
  } else if (elem.anchor === "top-left" || elem.anchor === "top-center") {
    startY = elem.y + size * 0.8;
  }
  
  lines.forEach((line, index) => {
    ctx.fillText(line, elem.x, startY + (index * lineHeight));
  });
  
  // Selection box dash around text boundary box
  if (isSelected) {
    // Approximate selection boundaries
    ctx.strokeStyle = "#6366f1";
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 3]);
    
    // Simple rough bbox estimation
    const metric = ctx.measureText(content);
    const boxW = maxW > 0 ? maxW : metric.width;
    let boxX = elem.x;
    
    if (elem.align === "center") boxX -= boxW / 2;
    else if (elem.align === "right") boxX -= boxW;
    
    let boxY = elem.y;
    if (elem.anchor === "center") boxY -= totalH / 2;
    
    ctx.strokeRect(boxX - 10, boxY - 10, boxW + 20, totalH + 20);
  }
  
  ctx.restore();
}

function wrapTextLines(text, context, maxWidth) {
  const words = text.split(" ");
  const lines = [];
  let currentLine = words[0];
  
  for (let i = 1; i < words.length; i++) {
    const word = words[i];
    const width = context.measureText(currentLine + " " + word).width;
    if (width < maxWidth) {
      currentLine += " " + word;
    } else {
      lines.push(currentLine);
      currentLine = word;
    }
  }
  lines.push(currentLine);
  return lines;
}

function drawGridOverlay() {
  const w = state.template.canvas_size[0];
  const h = state.template.canvas_size[1];
  
  ctx.save();
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 12]);
  
  // Draw grid intervals of 100px
  for (let x = 100; x < w; x += 100) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 100; y < h; y += 100) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
  
  ctx.restore();
}

// ─────────────────────────────────────────────────────────────────────────────
// Interactive Bounds Overlays (Selection DOM nodes mapping)
// ────────────────────────────────────────────────────────────────────────────

function updateOverlayBounds() {
  if (state.selectedElementIndex === null || state.cropState.active) {
    el.selectionBox.classList.add("hidden");
    return;
  }
  
  const elem = state.template.elements[state.selectedElementIndex];
  el.selectionBox.classList.remove("hidden");
  
  // Approximate sizes for mapping bounding overlay elements
  let w = 0;
  let h = 0;
  let tlx = 0;
  let tly = 0;
  
  if (elem.type === "image") {
    w = elem.width;
    h = elem.height;
    if (elem.anchor === "center") {
      tlx = elem.x - w / 2;
      tly = elem.y - h / 2;
    } else {
      tlx = elem.x;
      tly = elem.y;
    }
  } else if (elem.type === "text") {
    // Text bbox rough estimation
    ctx.save();
    const size = elem.font_size || 48;
    const font = elem.font_family || "Outfit-Regular";
    ctx.font = `${font.includes("Bold") ? "bold " : ""}${size}px "${font}", Arial`;
    
    const metric = ctx.measureText(getInterpolatedText(elem.content));
    w = elem.max_width > 0 ? elem.max_width : metric.width;
    h = size * 1.15;
    
    if (elem.align === "center") tlx = elem.x - w / 2;
    else if (elem.align === "right") tlx = elem.x - w;
    else tlx = elem.x;
    
    if (elem.anchor === "center") tly = elem.y - h / 2;
    else tly = elem.y;
    ctx.restore();
  }
  
  // Transform scale/offset from logical space to screen canvas wrapper CSS coordinates
  el.selectionBox.style.left = `${tlx * state.scale}px`;
  el.selectionBox.style.top = `${tly * state.scale}px`;
  el.selectionBox.style.width = `${w * state.scale}px`;
  el.selectionBox.style.height = `${h * state.scale}px`;
  
  // Transform rotation style
  if (elem.rotation) {
    el.selectionBox.style.transform = `rotate(${elem.rotation}deg)`;
  } else {
    el.selectionBox.style.transform = "none";
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Canvas Selection & Resizing Operations
// ────────────────────────────────────────────────────────────────────────────

function hitTest(lx, ly) {
  // Traverse backwards to select topmost item
  for (let i = state.template.elements.length - 1; i >= 0; i--) {
    const elem = state.template.elements[i];
    
    if (elem.type === "image") {
      const w = elem.width;
      const h = elem.height;
      let x1 = elem.x;
      let y1 = elem.y;
      
      if (elem.anchor === "center") {
        x1 -= w / 2;
        y1 -= h / 2;
      }
      const x2 = x1 + w;
      const y2 = y1 + h;
      
      if (lx >= x1 && lx <= x2 && ly >= y1 && ly <= y2) {
        return i;
      }
    } else if (elem.type === "text") {
      // Text coordinates hit check
      ctx.save();
      const size = elem.font_size || 48;
      const font = elem.font_family || "Outfit-Regular";
      ctx.font = `${font.toLowerCase().includes("bold") ? "bold " : ""}${size}px "${font}", Arial`;
      
      const metric = ctx.measureText(getInterpolatedText(elem.content));
      const w = elem.max_width > 0 ? elem.max_width : metric.width;
      const h = size * 1.2;
      ctx.restore();
      
      let x1 = elem.x;
      if (elem.align === "center") x1 -= w / 2;
      else if (elem.align === "right") x1 -= w;
      
      let y1 = elem.y;
      if (elem.anchor === "center") y1 -= h / 2;
      
      if (lx >= x1 && lx <= x1 + w && ly >= y1 && ly <= y1 + h) {
        return i;
      }
    }
  }
  return null;
}

function onCanvasMouseDown(e) {
  // If Crop mode is active, prevent standard selections
  if (state.cropState.active) return;
  
  const rect = el.canvasWrapper.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const lx = mouseX / state.scale;
  const ly = mouseY / state.scale;
  
  // 1. Check if clicking on a resize handle
  const handleNode = e.target.closest(".resize-handle");
  if (handleNode && state.selectedElementIndex !== null) {
    const handleType = handleNode.getAttribute("data-handle");
    const elem = state.template.elements[state.selectedElementIndex];
    
    let origW = elem.width || 200;
    let origH = elem.height || 200;
    
    if (elem.type === "text") {
      ctx.save();
      const size = elem.font_size || 48;
      const font = elem.font_family || "Outfit-Regular";
      ctx.font = `${font.toLowerCase().includes("bold") ? "bold " : ""}${size}px "${font}", Arial`;
      const metric = ctx.measureText(getInterpolatedText(elem.content));
      origW = elem.max_width > 0 ? elem.max_width : metric.width;
      origH = size * 1.15;
      ctx.restore();
    }
    
    state.dragState = {
      active: true,
      elementIndex: state.selectedElementIndex,
      mode: "resize",
      handle: handleType,
      startX: e.clientX,
      startY: e.clientY,
      origX: elem.x,
      origY: elem.y,
      origW: origW,
      origH: origH,
      origSize: elem.font_size || 48
    };
    
    saveUndoState();
    e.stopPropagation();
    return;
  }
  
  // 2. Otherwise do normal hit selection
  const hitIndex = hitTest(lx, ly);
  
  if (hitIndex !== null) {
    state.selectedElementIndex = hitIndex;
    const elem = state.template.elements[hitIndex];
    
    state.dragState = {
      active: true,
      elementIndex: hitIndex,
      mode: "move",
      startX: e.clientX,
      startY: e.clientY,
      origX: elem.x,
      origY: elem.y
    };
    
    saveUndoState();
  } else {
    // Deselect
    state.selectedElementIndex = null;
  }
  
  render();
  updatePropertiesPanel();
}

function onCanvasMouseMove(e) {
  if (!state.dragState.active) return;
  
  const drag = state.dragState;
  const elem = state.template.elements[drag.elementIndex];
  
  const dxScreen = e.clientX - drag.startX;
  const dyScreen = e.clientY - drag.startY;
  
  const dx = dxScreen / state.scale;
  const dy = dyScreen / state.scale;
  
  if (drag.mode === "move") {
    elem.x = Math.round(drag.origX + dx);
    elem.y = Math.round(drag.origY + dy);
  } else if (drag.mode === "resize") {
    const handle = drag.handle;
    
    if (elem.type === "text") {
      let scaleRatio = 1.0;
      if (handle.includes("r")) {
        scaleRatio = (drag.origW + dx) / drag.origW;
      } else if (handle.includes("l")) {
        scaleRatio = (drag.origW - dx) / drag.origW;
      } else if (handle.includes("b")) {
        scaleRatio = (drag.origH + dy) / drag.origH;
      } else if (handle.includes("t")) {
        scaleRatio = (drag.origH - dy) / drag.origH;
      }
      
      if (isNaN(scaleRatio) || scaleRatio <= 0.1) scaleRatio = 0.1;
      
      elem.font_size = Math.round(drag.origSize * scaleRatio);
      
      if (elem.font_size < 6) elem.font_size = 6;
      if (elem.font_size > 500) elem.font_size = 500;
      
      if (elem.max_width > 0) {
        elem.max_width = Math.round(elem.max_width * scaleRatio);
      }
    } else {
      // Proportional aspect ratio calculations if resizing image
      const origRatio = drag.origW / drag.origH;
      
      let newW = drag.origW;
      let newH = drag.origH;
      
      // Edge checks
      if (handle.includes("r")) newW = drag.origW + dx;
      if (handle.includes("l")) newW = drag.origW - dx;
      if (handle.includes("b")) newH = drag.origH + dy;
      if (handle.includes("t")) newH = drag.origH - dy;
      
      // Enforce limits
      newW = Math.max(20, newW);
      newH = Math.max(20, newH);
      
      // Preserve aspect ratio if corner handle is dragged
      if (handle === "tl" || handle === "tr" || handle === "bl" || handle === "br") {
        if (Math.abs(dx) > Math.abs(dy)) {
          newH = newW / origRatio;
        } else {
          newW = newH * origRatio;
        }
      }
      
      // Set properties
      elem.width = Math.round(newW);
      elem.height = Math.round(newH);
      
      // Adjust coordinates based on Top-left shifts if not center anchored
      if (elem.anchor !== "center") {
        if (handle.includes("l")) elem.x = Math.round(drag.origX + (drag.origW - newW));
        if (handle.includes("t")) elem.y = Math.round(drag.origY + (drag.origH - newH));
      }
    }
  }
  
  render();
  syncPanelInputs();
}

function onCanvasMouseUp() {
  if (state.dragState.active) {
    state.dragState.active = false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Cropping Tool implementation
// ────────────────────────────────────────────────────────────────────────────

function initCroppingTool() {
  if (state.selectedElementIndex === null) return;
  const elem = state.template.elements[state.selectedElementIndex];
  if (elem.type !== "image") return;
  
  state.cropState.active = true;
  state.cropState.originalCrop = elem.crop ? { ...elem.crop } : null;
  
  // Display Crop Confirmation box controls
  el.btnTriggerCrop.classList.add("hidden");
  el.cropStatusBox.classList.remove("hidden");
  
  // Display crop handles box overlay
  const croppers = el.selectionBox.querySelectorAll(".crop-handle");
  croppers.forEach(h => h.classList.remove("hidden"));
  const resizers = el.selectionBox.querySelectorAll(".resize-handle");
  resizers.forEach(h => h.classList.add("hidden"));
  
  // Enter visual cropping darker background mode
  el.overlay.classList.add("cropping-mode-active");
  
  // Crop mode is basically mouse drag bounds setup
  // To keep it simple, we draw thick brackets inside CSS over the selection box
  // We attach custom crop sliders or allow adjusting width/height
}

function confirmCropping() {
  state.cropState.active = false;
  el.btnTriggerCrop.classList.remove("hidden");
  el.cropStatusBox.classList.add("hidden");
  
  const croppers = el.selectionBox.querySelectorAll(".crop-handle");
  croppers.forEach(h => h.classList.add("hidden"));
  const resizers = el.selectionBox.querySelectorAll(".resize-handle");
  resizers.forEach(h => h.classList.remove("hidden"));
  
  render();
}

function cancelCropping() {
  state.cropState.active = false;
  el.btnTriggerCrop.classList.remove("hidden");
  el.cropStatusBox.classList.add("hidden");
  
  // Restore original crop settings
  const elem = state.template.elements[state.selectedElementIndex];
  if (state.cropState.originalCrop) {
    elem.crop = state.cropState.originalCrop;
  } else {
    delete elem.crop;
  }
  
  const croppers = el.selectionBox.querySelectorAll(".crop-handle");
  croppers.forEach(h => h.classList.add("hidden"));
  const resizers = el.selectionBox.querySelectorAll(".resize-handle");
  resizers.forEach(h => h.classList.remove("hidden"));
  
  render();
}

// Set of font families already loaded locally (populated by loadLocalFonts)
const _loadedLocalFonts = new Set();

/**
 * Fetches all font files from assets/fonts via the server API and registers
 * them as @font-face CSS rules so the browser canvas can render them.
 */
function loadLocalFonts() {
  fetch("/api/fonts/list")
    .then(res => res.json())
    .then(data => {
      if (!data.fonts || !data.fonts.length) return;
      
      let styleText = "";
      data.fonts.forEach(font => {
        _loadedLocalFonts.add(font.family.toLowerCase());
        styleText += `
@font-face {
  font-family: "${font.family}";
  src: url("${font.url}") format("truetype");
  font-display: swap;
}
`;
      });
      
      const styleEl = document.createElement("style");
      styleEl.id = "local-fonts-styles";
      styleEl.textContent = styleText;
      document.head.appendChild(styleEl);
      
      console.log(`Loaded ${data.fonts.length} local fonts for canvas rendering.`);
      
      // Re-render after fonts are registered so canvas text updates
      setTimeout(() => render(), 300);
    })
    .catch(err => console.error("Failed to load local fonts:", err));
}

/**
 * Injects a Google Fonts stylesheet for fonts NOT available locally.
 * Skips fonts that were already registered via loadLocalFonts().
 */
function injectGoogleFontStylesheet(fontName) {
  if (!fontName) return;
  
  // Skip if this font is already loaded locally from assets/fonts
  const cleanName = fontName.replace(/\s+/g, "").replace(/-/g, "").toLowerCase();
  for (const local of _loadedLocalFonts) {
    const localClean = local.replace(/\s+/g, "").replace(/-/g, "").toLowerCase();
    if (localClean === cleanName) return;
  }
  
  const linkId = `gfont-${fontName.replace(/\s+/g, "-").toLowerCase()}`;
  if (document.getElementById(linkId)) return;
  
  const link = document.createElement("link");
  link.id = linkId;
  link.rel = "stylesheet";
  link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(fontName)}:wght@400;700&display=swap`;
  
  document.head.appendChild(link);
  
  // Inform python server backend to download & cache font TTF
  fetch("/api/fonts/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ font_family: fontName })
  }).then(res => res.json())
    .then(data => {
      console.log("Font cached:", data.message);
    }).catch(err => console.error("Font server fetch error:", err));
}

// ─────────────────────────────────────────────────────────────────────────────
// Properties Panel Controller & Binding syncs
// ────────────────────────────────────────────────────────────────────────────

function setupPropertyInputs() {
  // Sync canvas properties inputs
  el.canvasW.addEventListener("change", () => {
    state.template.canvas_size[0] = parseInt(el.canvasW.value) || 2000;
    updateZoomUI();
  });
  el.canvasH.addEventListener("change", () => {
    state.template.canvas_size[1] = parseInt(el.canvasH.value) || 2000;
    updateZoomUI();
  });
  
  // Sync Background Properties
  el.bgType.addEventListener("change", (e) => {
    saveUndoState();
    state.template.background = state.template.background || {};
    state.template.background.type = e.target.value;
    
    if (e.target.value === "gradient") {
      el.bgSolidCtrls.classList.add("hidden");
      el.bgGradCtrls.classList.remove("hidden");
      state.template.background.color_start = el.bgGradStart.value;
      state.template.background.color_end = el.bgGradEnd.value;
    } else {
      el.bgSolidCtrls.classList.remove("hidden");
      el.bgGradCtrls.classList.add("hidden");
      state.template.background.color = el.bgColor.value;
    }
    render();
  });
  
  el.bgColor.addEventListener("input", (e) => {
    el.bgColorHex.value = e.target.value;
    state.template.background.color = e.target.value;
    render();
  });
  el.bgColorHex.addEventListener("change", (e) => {
    if (e.target.value.startsWith("#") && e.target.value.length === 7) {
      el.bgColor.value = e.target.value;
      state.template.background.color = e.target.value;
      render();
    }
  });
  
  el.bgGradStart.addEventListener("input", (e) => {
    state.template.background.color_start = e.target.value;
    render();
  });
  el.bgGradEnd.addEventListener("input", (e) => {
    state.template.background.color_end = e.target.value;
    render();
  });
  
  // --- Sync Image element inputs ---
  el.imgCategory.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    state.template.elements[state.selectedElementIndex].source.category = e.target.value;
    render();
  });
  
  el.imgIndex.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    state.template.elements[state.selectedElementIndex].source.index = parseInt(e.target.value) || 0;
    render();
  });
  
  const imgCoordInputs = [el.imgX, el.imgY, el.imgW, el.imgH, el.imgRot];
  imgCoordInputs.forEach(input => {
    input.addEventListener("change", () => {
      if (state.selectedElementIndex === null) return;
      saveUndoState();
      const elem = state.template.elements[state.selectedElementIndex];
      elem.x = parseInt(el.imgX.value) || 0;
      elem.y = parseInt(el.imgY.value) || 0;
      elem.width = parseInt(el.imgW.value) || 100;
      elem.height = parseInt(el.imgH.value) || 100;
      elem.rotation = parseInt(el.imgRot.value) || 0;
      render();
    });
  });
  
  el.imgAnchor.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    state.template.elements[state.selectedElementIndex].anchor = e.target.value;
    render();
  });
  
  // Cropper trigger buttons
  el.btnTriggerCrop.addEventListener("click", initCroppingTool);
  el.btnCropConfirm.addEventListener("click", confirmCropping);
  el.btnCropCancel.addEventListener("click", cancelCropping);
  
  // Visual Effects checklist binding
  el.chkOutline.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    const elem = state.template.elements[state.selectedElementIndex];
    elem.effects = elem.effects || {};
    
    if (e.target.checked) {
      el.outlineSub.classList.remove("hidden");
      elem.effects.outline = {
        color: el.olColor.value,
        width: parseInt(el.olWidth.value) || 10
      };
    } else {
      el.outlineSub.classList.add("hidden");
      delete elem.effects.outline;
      if (Object.keys(elem.effects).length === 0) delete elem.effects;
    }
  });
  
  el.olWidth.addEventListener("change", () => {
    if (state.selectedElementIndex === null) return;
    const elem = state.template.elements[state.selectedElementIndex];
    if (elem.effects && elem.effects.outline) {
      elem.effects.outline.width = parseInt(el.olWidth.value) || 10;
    }
  });
  
  el.olColor.addEventListener("input", (e) => {
    if (state.selectedElementIndex === null) return;
    const elem = state.template.elements[state.selectedElementIndex];
    if (elem.effects && elem.effects.outline) {
      elem.effects.outline.color = e.target.value;
    }
  });
  
  el.chkShadow.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    const elem = state.template.elements[state.selectedElementIndex];
    elem.effects = elem.effects || {};
    
    if (e.target.checked) {
      el.shadowSub.classList.remove("hidden");
      elem.effects.shadow = {
        color: el.shColor.value + "40", // 25% opacity default
        blur: parseInt(el.shBlur.value) || 15,
        offset: [parseInt(el.shDx.value) || 10, parseInt(el.shDy.value) || 10]
      };
    } else {
      el.shadowSub.classList.add("hidden");
      delete elem.effects.shadow;
      if (Object.keys(elem.effects).length === 0) delete elem.effects;
    }
  });
  
  const shadowInputs = [el.shBlur, el.shDx, el.shDy];
  shadowInputs.forEach(input => {
    input.addEventListener("change", () => {
      if (state.selectedElementIndex === null) return;
      const elem = state.template.elements[state.selectedElementIndex];
      if (elem.effects && elem.effects.shadow) {
        elem.effects.shadow.blur = parseInt(el.shBlur.value) || 15;
        elem.effects.shadow.offset = [parseInt(el.shDx.value) || 10, parseInt(el.shDy.value) || 10];
      }
    });
  });
  
  el.shColor.addEventListener("input", (e) => {
    if (state.selectedElementIndex === null) return;
    const elem = state.template.elements[state.selectedElementIndex];
    if (elem.effects && elem.effects.shadow) {
      elem.effects.shadow.color = e.target.value + "40";
    }
  });
  
  // --- Sync Text element inputs ---
  el.textContent.addEventListener("input", (e) => {
    if (state.selectedElementIndex === null) return;
    state.template.elements[state.selectedElementIndex].content = e.target.value;
    render();
  });
  
  // Font Explorer panel search filter
  el.fontSearch.addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    const options = el.textFont.querySelectorAll("option");
    
    options.forEach(opt => {
      if (opt.textContent.toLowerCase().includes(query)) {
        opt.style.display = "";
      } else {
        opt.style.display = "none";
      }
    });
  });
  
  el.textFont.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    const fontName = e.target.value;
    state.template.elements[state.selectedElementIndex].font_family = fontName;
    
    // Auto web stylesheet link download check
    injectGoogleFontStylesheet(fontName);
    render();
  });
  
  el.textSize.addEventListener("change", () => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    state.template.elements[state.selectedElementIndex].font_size = parseInt(el.textSize.value) || 48;
    render();
  });
  
  el.textColor.addEventListener("input", (e) => {
    el.textColorHex.value = e.target.value;
    if (state.selectedElementIndex === null) return;
    state.template.elements[state.selectedElementIndex].color = e.target.value;
    render();
  });
  
  el.textColorHex.addEventListener("change", (e) => {
    if (e.target.value.startsWith("#") && e.target.value.length === 7) {
      el.textColor.value = e.target.value;
      if (state.selectedElementIndex === null) return;
      state.template.elements[state.selectedElementIndex].color = e.target.value;
      render();
    }
  });
  
  el.textAlign.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    state.template.elements[state.selectedElementIndex].align = e.target.value;
    render();
  });
  
  el.textAnchor.addEventListener("change", (e) => {
    if (state.selectedElementIndex === null) return;
    saveUndoState();
    state.template.elements[state.selectedElementIndex].anchor = e.target.value;
    render();
  });
  
  const textCoordInputs = [el.textX, el.textY, el.textMaxW];
  textCoordInputs.forEach(input => {
    input.addEventListener("change", () => {
      if (state.selectedElementIndex === null) return;
      saveUndoState();
      const elem = state.template.elements[state.selectedElementIndex];
      elem.x = parseInt(el.textX.value) || 0;
      elem.y = parseInt(el.textY.value) || 0;
      elem.max_width = parseInt(el.textMaxW.value) || 0;
      render();
    });
  });
}

function updatePropertiesPanel() {
  if (state.selectedElementIndex === null) {
    el.propNoSelection.classList.remove("hidden");
    el.propImagePanel.classList.add("hidden");
    el.propTextPanel.classList.add("hidden");
    return;
  }
  
  const elem = state.template.elements[state.selectedElementIndex];
  
  if (elem.type === "image") {
    el.propNoSelection.classList.add("hidden");
    el.propImagePanel.classList.remove("hidden");
    el.propTextPanel.classList.add("hidden");
    
    // Load inputs
    el.imgCategory.value = elem.source.category;
    el.imgIndex.value = elem.source.index;
    el.imgX.value = elem.x;
    el.imgY.value = elem.y;
    el.imgW.value = elem.width;
    el.imgH.value = elem.height;
    el.imgRot.value = elem.rotation || 0;
    el.imgAnchor.value = elem.anchor || "center";
    
    // Effects
    const eff = elem.effects || {};
    el.chkOutline.checked = !!eff.outline;
    if (eff.outline) {
      el.outlineSub.classList.remove("hidden");
      el.olWidth.value = eff.outline.width;
      el.olColor.value = eff.outline.color;
    } else {
      el.outlineSub.classList.add("hidden");
    }
    
    el.chkShadow.checked = !!eff.shadow;
    if (eff.shadow) {
      el.shadowSub.classList.remove("hidden");
      el.shBlur.value = eff.shadow.blur;
      el.shColor.value = eff.shadow.color.substring(0, 7); // Strip alpha transparency suffix
      el.shDx.value = eff.shadow.offset[0];
      el.shDy.value = eff.shadow.offset[1];
    } else {
      el.shadowSub.classList.add("hidden");
    }
  } else if (elem.type === "text") {
    el.propNoSelection.classList.add("hidden");
    el.propImagePanel.classList.add("hidden");
    el.propTextPanel.classList.remove("hidden");
    
    el.textContent.value = elem.content;
    el.textFont.value = elem.font_family;
    el.textSize.value = elem.font_size;
    el.textColor.value = elem.color;
    el.textColorHex.value = elem.color;
    el.textAlign.value = elem.align || "center";
    el.textAnchor.value = elem.anchor || "center";
    el.textX.value = elem.x;
    el.textY.value = elem.y;
    el.textMaxW.value = elem.max_width || 0;
  }
}

// Sync values during active mouse dragging resizing
function syncPanelInputs() {
  if (state.selectedElementIndex === null) return;
  const elem = state.template.elements[state.selectedElementIndex];
  
  if (elem.type === "image") {
    el.imgX.value = elem.x;
    el.imgY.value = elem.y;
    el.imgW.value = elem.width;
    el.imgH.value = elem.height;
  } else if (elem.type === "text") {
    el.textX.value = elem.x;
    el.textY.value = elem.y;
    el.textSize.value = elem.font_size;
    if (elem.max_width > 0) {
      el.textMaxW.value = elem.max_width;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Undo/Redo Engine
// ────────────────────────────────────────────────────────────────────────────

function saveUndoState() {
  state.undoStack.push(JSON.stringify(state.template));
  state.redoStack = []; // Clear redo stack on new action
  if (state.undoStack.length > 30) state.undoStack.shift();
}

window.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "z") {
    e.preventDefault();
    performUndo();
  }
  if (e.key === "Delete" && state.selectedElementIndex !== null) {
    deleteSelectedElement();
  }
});

function performUndo() {
  if (state.undoStack.length === 0) return;
  
  state.redoStack.push(JSON.stringify(state.template));
  state.template = JSON.parse(state.undoStack.pop());
  
  // Clamp selected item bounds
  if (state.selectedElementIndex >= state.template.elements.length) {
    state.selectedElementIndex = state.template.elements.length > 0 ? 0 : null;
  }
  
  render();
  updatePropertiesPanel();
}

// ─────────────────────────────────────────────────────────────────────────────
// Generate Mockup Output Preview via Server
// ────────────────────────────────────────────────────────────────────────────

async function generateMockupPreview() {
  if (!state.masterPath) {
    alert("Please load a Theme Folder first before rendering a preview.");
    return;
  }
  
  el.btnGenerate.textContent = "⚡ Generating...";
  el.btnGenerate.disabled = true;
  
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template: state.template,
        filename: state.selectedFilename || "active_editor_template.json"
      })
    });
    
    const data = await res.json();
    el.btnGenerate.textContent = "⚡ Generate Preview";
    el.btnGenerate.disabled = false;
    
    if (data.error) {
      alert("Generator Error: " + data.error);
      return;
    }
    
    // Display Modal
    el.previewImg.src = data.preview_url;
    el.previewPath.textContent = `Generated Output Saved to: ${data.output_path}`;
    el.modalPreview.classList.remove("hidden");
  } catch (err) {
    el.btnGenerate.textContent = "⚡ Generate Preview";
    el.btnGenerate.disabled = false;
    alert("Network preview generation failed: " + err);
  }
}
