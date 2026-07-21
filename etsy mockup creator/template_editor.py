"""
Visual Drag & Drop Template Editor for Etsy Mockup Creator.

A Tkinter-based GUI that lets you visually design mockup templates by placing
image and text elements on a canvas, editing their properties, and exporting
the result as a JSON template file compatible with the mockup generator pipeline.

Usage:
    python template_editor.py

Requirements:
    - Python 3.8+
    - Pillow (already in requirements.txt)
    - Tkinter (built into Python)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import json
import os
import copy

from PIL import Image, ImageTk

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_COLORS = {
    "character":    "#3B82F6",
    "prop":         "#EF4444",
    "combo":        "#10B981",
    "pattern":      "#F59E0B",
    "scene":        "#8B5CF6",
    "subcharacter": "#06B6D4",
}

CATEGORIES    = ["character", "prop", "combo", "pattern", "scene", "subcharacter"]
FONT_FAMILIES = ["Outfit-Bold", "Outfit-Regular"]
ANCHORS       = ["center", "top-left", "top-center"]
ALIGNS        = ["center", "left", "right"]
BG_TYPES      = ["solid", "gradient", "image"]

HANDLE_SIZE  = 5
GRID_SPACING = 100
MAX_UNDO     = 50


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

class TemplateEditor:
    """Visual drag-and-drop editor for Etsy mockup JSON templates."""

    # ═════════════════════════════════════════════════════════════════════════
    # Initialization
    # ═════════════════════════════════════════════════════════════════════════

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Etsy Mockup — Template Editor")
        self.root.geometry("1500x920")
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass

        # ── Template state ──
        self.template    = self._default_template()
        self.current_file = None

        # ── Selection & interaction ──
        self.selected_idx = None
        self.scale        = 0.40
        self.offset_x     = 20
        self.offset_y     = 20

        # Drag bookkeeping
        self._drag_idx       = None
        self._drag_start_sx  = 0
        self._drag_start_sy  = 0
        self._drag_orig_lx   = 0
        self._drag_orig_ly   = 0
        self._pre_drag_state = None

        # ── Theme preview ──
        self.theme_dir      = None
        self.indexed_images = {}            # category → [paths]
        self._photo_refs    = []            # prevent GC of ImageTk objects

        # ── Undo / redo ──
        self.undo_stack = []
        self.redo_stack = []

        # ── UI variables ──
        self.show_grid = tk.BooleanVar(value=True)

        # ── Build ──
        self._build_menu()
        self._build_toolbar()
        self._build_main_pane()
        self._build_statusbar()
        self._bind_keys()

        # Initial render (after the window has geometry)
        self.root.after(50, self._refresh_all)

    # ═════════════════════════════════════════════════════════════════════════
    # Default data
    # ═════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _default_template():
        return {
            "name": "New Template",
            "canvas_size": [2000, 2000],
            "background": {"type": "solid", "color": "#FFFFFF"},
            "elements": [],
        }

    # ═════════════════════════════════════════════════════════════════════════
    # UI construction
    # ═════════════════════════════════════════════════════════════════════════

    def _build_menu(self):
        mb = tk.Menu(self.root)

        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="New Template",       command=self.new_template,  accelerator="Ctrl+N")
        fm.add_command(label="Open JSON…",         command=self.open_template, accelerator="Ctrl+O")
        fm.add_separator()
        fm.add_command(label="Save",               command=self.save_template, accelerator="Ctrl+S")
        fm.add_command(label="Save As…",           command=self.save_as)
        fm.add_separator()
        fm.add_command(label="Load Theme Folder…", command=self.load_theme)
        fm.add_separator()
        fm.add_command(label="Exit",               command=self.root.quit)
        mb.add_cascade(label="File", menu=fm)

        em = tk.Menu(mb, tearoff=0)
        em.add_command(label="Undo",      command=self.undo,              accelerator="Ctrl+Z")
        em.add_command(label="Redo",      command=self.redo,              accelerator="Ctrl+Y")
        em.add_separator()
        em.add_command(label="Delete",    command=self.delete_element,    accelerator="Del")
        em.add_command(label="Duplicate", command=self.duplicate_element, accelerator="Ctrl+D")
        mb.add_cascade(label="Edit", menu=em)

        vm = tk.Menu(mb, tearoff=0)
        vm.add_checkbutton(label="Show Grid", variable=self.show_grid,
                           command=self._refresh_canvas)
        vm.add_separator()
        vm.add_command(label="Zoom In",       command=lambda: self._zoom(1.15))
        vm.add_command(label="Zoom Out",      command=lambda: self._zoom(1 / 1.15))
        vm.add_command(label="Fit to Window", command=self._fit_zoom)
        mb.add_cascade(label="View", menu=vm)

        self.root.config(menu=mb)

    def _build_toolbar(self):
        tb = ttk.Frame(self.root, padding=(5, 4))
        tb.pack(side="top", fill="x")

        ttk.Button(tb, text="+ Image",    command=self.add_image_element, width=9).pack(side="left", padx=2)
        ttk.Button(tb, text="+ Text",     command=self.add_text_element,  width=9).pack(side="left", padx=2)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6, pady=2)
        ttk.Button(tb, text="Delete",     command=self.delete_element,    width=8).pack(side="left", padx=2)
        ttk.Button(tb, text="Duplicate",  command=self.duplicate_element, width=9).pack(side="left", padx=2)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6, pady=2)
        ttk.Button(tb, text="▲ Up",       command=self.move_layer_up,     width=6).pack(side="left", padx=2)
        ttk.Button(tb, text="▼ Down",     command=self.move_layer_down,   width=6).pack(side="left", padx=2)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6, pady=2)
        ttk.Button(tb, text="Load Theme", command=self.load_theme,        width=11).pack(side="left", padx=2)

        # Zoom controls (right-aligned)
        ttk.Button(tb, text="Fit", command=self._fit_zoom, width=4).pack(side="right", padx=2)
        ttk.Button(tb, text="−",   command=lambda: self._zoom(1 / 1.15), width=3).pack(side="right")
        self.zoom_lbl = ttk.Label(tb, text="40 %", width=6, anchor="center")
        self.zoom_lbl.pack(side="right")
        ttk.Button(tb, text="+",   command=lambda: self._zoom(1.15), width=3).pack(side="right")

    def _build_main_pane(self):
        pane = ttk.PanedWindow(self.root, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # ── Left: canvas ──
        cf = ttk.Frame(pane)
        pane.add(cf, weight=3)
        self.canvas = tk.Canvas(cf, bg="#1F2937", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True)

        # ── Right: sidebar ──
        right = ttk.Frame(pane, width=350)
        pane.add(right, weight=0)

        # Element list
        lf = ttk.LabelFrame(right, text="Elements  (layer order)", padding=5)
        lf.pack(fill="x", padx=4, pady=(4, 2))

        list_box = ttk.Frame(lf)
        list_box.pack(fill="x")
        self.elem_listbox = tk.Listbox(list_box, height=10, font=("Consolas", 9),
                                       activestyle="none", selectbackground="#3B82F6",
                                       selectforeground="white")
        lsb = ttk.Scrollbar(list_box, orient="vertical", command=self.elem_listbox.yview)
        self.elem_listbox.config(yscrollcommand=lsb.set)
        self.elem_listbox.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")
        self.elem_listbox.bind("<<ListboxSelect>>", self._on_list_select)

        # Properties panel (scrollable)
        pf = ttk.LabelFrame(right, text="Properties", padding=5)
        pf.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        self._prop_canvas = tk.Canvas(pf, highlightthickness=0)
        psb = ttk.Scrollbar(pf, orient="vertical", command=self._prop_canvas.yview)
        self.prop_frame = ttk.Frame(self._prop_canvas)

        self.prop_frame.bind("<Configure>",
            lambda e: self._prop_canvas.configure(scrollregion=self._prop_canvas.bbox("all")))
        self._prop_win_id = self._prop_canvas.create_window((0, 0), window=self.prop_frame, anchor="nw")
        self._prop_canvas.configure(yscrollcommand=psb.set)
        self._prop_canvas.bind("<Configure>",
            lambda e: self._prop_canvas.itemconfig(self._prop_win_id, width=e.width))

        self._prop_canvas.pack(side="left", fill="both", expand=True)
        psb.pack(side="right", fill="y")

        # Scroll the properties pane with mousewheel
        def _prop_scroll(e):
            self._prop_canvas.yview_scroll(-1 * (e.delta // 120), "units")
        self._prop_canvas.bind("<MouseWheel>", _prop_scroll)
        self.prop_frame.bind("<MouseWheel>", _prop_scroll)

    def _build_statusbar(self):
        sb = ttk.Frame(self.root, padding=(6, 2))
        sb.pack(side="bottom", fill="x")
        self.status_lbl = ttk.Label(sb, text="Ready")
        self.status_lbl.pack(side="left")
        self.coord_lbl = ttk.Label(sb, text="")
        self.coord_lbl.pack(side="right")

    def _bind_keys(self):
        self.root.bind("<Control-n>", lambda e: self.new_template())
        self.root.bind("<Control-o>", lambda e: self.open_template())
        self.root.bind("<Control-s>", lambda e: self.save_template())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-d>", lambda e: self.duplicate_element())
        self.root.bind("<Delete>",    lambda e: self.delete_element())
        self.root.bind("<Escape>",    lambda e: self._deselect())

        # Arrow nudge (1px per tap, 10px with Shift)
        self.root.bind("<Up>",        lambda e: self._nudge(0, -1))
        self.root.bind("<Down>",      lambda e: self._nudge(0, 1))
        self.root.bind("<Left>",      lambda e: self._nudge(-1, 0))
        self.root.bind("<Right>",     lambda e: self._nudge(1, 0))
        self.root.bind("<Shift-Up>",    lambda e: self._nudge(0, -10))
        self.root.bind("<Shift-Down>",  lambda e: self._nudge(0, 10))
        self.root.bind("<Shift-Left>",  lambda e: self._nudge(-10, 0))
        self.root.bind("<Shift-Right>", lambda e: self._nudge(10, 0))

        # Canvas mouse
        self.canvas.bind("<Button-1>",       self._on_canvas_click)
        self.canvas.bind("<B1-Motion>",      self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>",self._on_canvas_release)
        self.canvas.bind("<MouseWheel>",     self._on_canvas_scroll)
        self.canvas.bind("<Motion>",         self._on_canvas_motion)
        self.canvas.bind("<Configure>",      lambda e: self._refresh_canvas())

    # ═════════════════════════════════════════════════════════════════════════
    # Coordinate helpers
    # ═════════════════════════════════════════════════════════════════════════

    def _to_screen(self, lx, ly):
        """Logical template coords → screen canvas-widget coords."""
        return lx * self.scale + self.offset_x, ly * self.scale + self.offset_y

    def _to_logical(self, sx, sy):
        """Screen coords → logical template coords."""
        return (sx - self.offset_x) / self.scale, (sy - self.offset_y) / self.scale

    # ═════════════════════════════════════════════════════════════════════════
    # Canvas rendering
    # ═════════════════════════════════════════════════════════════════════════

    def _refresh_all(self):
        self._refresh_element_list()
        self._refresh_canvas()
        self._refresh_properties()
        self._update_status()

    def _refresh_canvas(self):
        self.canvas.delete("all")
        self._photo_refs.clear()

        cw, ch = self.template["canvas_size"]

        # Auto-center the template on the widget
        ww = max(self.canvas.winfo_width(), 300)
        wh = max(self.canvas.winfo_height(), 300)
        self.offset_x = max(20, (ww - cw * self.scale) / 2)
        self.offset_y = max(20, (wh - ch * self.scale) / 2)

        sx1, sy1 = self._to_screen(0, 0)
        sx2, sy2 = self._to_screen(cw, ch)

        # Canvas shadow
        self.canvas.create_rectangle(sx1 + 5, sy1 + 5, sx2 + 5, sy2 + 5,
                                     fill="#111827", outline="")

        # Canvas background
        bg_color = self.template.get("background", {}).get("color", "#FFFFFF")
        self.canvas.create_rectangle(sx1, sy1, sx2, sy2,
                                     fill=bg_color, outline="#6B7280", width=1)

        # Grid
        if self.show_grid.get():
            self._draw_grid(cw, ch)

        # Elements (first = bottom layer, last = top)
        for i, elem in enumerate(self.template["elements"]):
            self._draw_element(i, elem)

        # Selection highlight
        if (self.selected_idx is not None
                and 0 <= self.selected_idx < len(self.template["elements"])):
            self._draw_selection_handles(self.selected_idx)

    # ── Grid ──

    def _draw_grid(self, cw, ch):
        for x in range(0, cw + 1, GRID_SPACING):
            s1 = self._to_screen(x, 0)
            s2 = self._to_screen(x, ch)
            self.canvas.create_line(s1[0], s1[1], s2[0], s2[1],
                                    fill="#E5E7EB", dash=(2, 4))
        for y in range(0, ch + 1, GRID_SPACING):
            s1 = self._to_screen(0, y)
            s2 = self._to_screen(cw, y)
            self.canvas.create_line(s1[0], s1[1], s2[0], s2[1],
                                    fill="#E5E7EB", dash=(2, 4))

    # ── Elements ──

    def _draw_element(self, idx, elem):
        tag = f"elem_{idx}"
        if elem["type"] == "image":
            self._draw_image_elem(idx, elem, tag)
        elif elem["type"] == "text":
            self._draw_text_elem(idx, elem, tag)

    def _draw_image_elem(self, idx, elem, tag):
        lx, ly   = elem.get("x", 0), elem.get("y", 0)
        lw, lh   = elem.get("width", 200), elem.get("height", 200)
        anchor   = elem.get("anchor", "center")
        category = elem.get("source", {}).get("category", "character")
        index    = elem.get("source", {}).get("index", 0)

        # Compute top-left in logical space
        if anchor in ("center", "middle"):
            tlx, tly = lx - lw / 2, ly - lh / 2
        else:
            tlx, tly = lx, ly

        sx1, sy1 = self._to_screen(tlx, tly)
        sx2, sy2 = self._to_screen(tlx + lw, tly + lh)
        sw = max(1, int(sx2 - sx1))
        sh = max(1, int(sy2 - sy1))

        # Try real theme image
        drawn = False
        if self.indexed_images:
            cat_imgs = self.indexed_images.get(category, [])
            if cat_imgs:
                img_path = cat_imgs[index % len(cat_imgs)]
                try:
                    pil = Image.open(img_path).convert("RGBA")
                    pil = pil.resize((sw, sh), Image.Resampling.LANCZOS)
                    # Composite onto checkerboard-ish bg for transparency
                    bg = Image.new("RGBA", pil.size, (240, 240, 240, 255))
                    comp = Image.alpha_composite(bg, pil)
                    tk_img = ImageTk.PhotoImage(comp)
                    self._photo_refs.append(tk_img)
                    self.canvas.create_image(sx1, sy1, image=tk_img, anchor="nw", tags=tag)
                    # Thin border
                    self.canvas.create_rectangle(sx1, sy1, sx2, sy2,
                                                 outline="#9CA3AF", width=1, tags=tag)
                    drawn = True
                except Exception:
                    pass

        if not drawn:
            # Placeholder rectangle
            color = CATEGORY_COLORS.get(category, "#6B7280")
            self.canvas.create_rectangle(sx1, sy1, sx2, sy2,
                                         fill=color, outline="#FFF", width=1,
                                         stipple="gray25", tags=tag)
            label = f"{category}[{index}]"
            cx, cy = (sx1 + sx2) / 2, (sy1 + sy2) / 2
            self.canvas.create_text(cx, cy, text=label, fill="white",
                                    font=("Consolas", 9, "bold"), tags=tag)

    def _draw_text_elem(self, idx, elem, tag):
        lx, ly      = elem.get("x", 0), elem.get("y", 0)
        content     = elem.get("content", "Text")
        font_size   = elem.get("font_size", 48)
        color       = elem.get("color", "#000000")
        anchor      = elem.get("anchor", "center")
        font_family = elem.get("font_family", "Outfit-Regular")

        sx, sy = self._to_screen(lx, ly)
        disp_size = max(8, int(font_size * self.scale * 0.75))

        tk_anchor = "center"
        if anchor == "top-left":
            tk_anchor = "nw"
        elif anchor == "top-center":
            tk_anchor = "n"

        weight = "bold" if "Bold" in font_family else "normal"

        self.canvas.create_text(sx, sy, text=content, fill=color,
                                font=("Arial", disp_size, weight),
                                anchor=tk_anchor, tags=tag)

        # Dashed bounding indicator
        bbox = self.canvas.bbox(tag)
        if bbox:
            self.canvas.create_rectangle(bbox[0] - 2, bbox[1] - 2,
                                         bbox[2] + 2, bbox[3] + 2,
                                         outline="#9CA3AF", width=1, dash=(4, 4),
                                         tags=tag)

    # ── Selection handles ──

    def _draw_selection_handles(self, idx):
        bbox = self.canvas.bbox(f"elem_{idx}")
        if not bbox:
            return
        x1, y1, x2, y2 = bbox

        self.canvas.create_rectangle(x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                                     outline="#3B82F6", width=2, dash=(6, 3),
                                     tags="sel")
        hs = HANDLE_SIZE
        for hx, hy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
            self.canvas.create_rectangle(hx - hs, hy - hs, hx + hs, hy + hs,
                                         fill="#3B82F6", outline="white", width=1,
                                         tags="sel")

    # ═════════════════════════════════════════════════════════════════════════
    # Element list (right sidebar)
    # ═════════════════════════════════════════════════════════════════════════

    def _refresh_element_list(self):
        self.elem_listbox.delete(0, "end")
        for i, elem in enumerate(self.template["elements"]):
            if elem["type"] == "image":
                src = elem.get("source", {})
                lbl = f"{i+1}. img  {src.get('category','?')}[{src.get('index',0)}]"
            else:
                txt = elem.get("content", "")
                if len(txt) > 18:
                    txt = txt[:18] + "…"
                lbl = f'{i+1}. txt  "{txt}"'
            self.elem_listbox.insert("end", lbl)

        if self.selected_idx is not None and self.selected_idx < self.elem_listbox.size():
            self.elem_listbox.selection_clear(0, "end")
            self.elem_listbox.selection_set(self.selected_idx)
            self.elem_listbox.see(self.selected_idx)

    def _on_list_select(self, _event):
        sel = self.elem_listbox.curselection()
        self.selected_idx = sel[0] if sel else None
        self._refresh_canvas()
        self._refresh_properties()

    # ═════════════════════════════════════════════════════════════════════════
    # Properties panel
    # ═════════════════════════════════════════════════════════════════════════

    def _refresh_properties(self):
        for w in self.prop_frame.winfo_children():
            w.destroy()

        if (self.selected_idx is None
                or self.selected_idx >= len(self.template["elements"])):
            self._show_canvas_props()
            return

        elem = self.template["elements"][self.selected_idx]
        header = f"Element #{self.selected_idx + 1}  —  {elem['type'].upper()}"
        ttk.Label(self.prop_frame, text=header,
                  font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(0, 8))

        if elem["type"] == "image":
            self._show_image_props(elem)
        elif elem["type"] == "text":
            self._show_text_props(elem)

    # ── Canvas-level properties ──

    def _show_canvas_props(self):
        ttk.Label(self.prop_frame, text="Template Settings",
                  font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(0, 8))
        self._add_entry("Name", self.template, "name")

        self._section("Canvas Size")
        row = ttk.Frame(self.prop_frame)
        row.pack(fill="x", padx=4, pady=2)
        self._add_inline_spin(row, "W:", self.template["canvas_size"], 0, 100, 10000)
        self._add_inline_spin(row, "H:", self.template["canvas_size"], 1, 100, 10000)

        self._section("Background")
        bg = self.template.setdefault("background", {"type": "solid", "color": "#FFFFFF"})
        self._add_combo("Type", bg, "type", BG_TYPES)
        if bg.get("type") == "solid":
            self._add_color("Color", bg, "color")
        elif bg.get("type") == "gradient":
            bg.setdefault("color_start", "#FFFFFF")
            bg.setdefault("color_end", "#CCCCCC")
            self._add_color("Start", bg, "color_start")
            self._add_color("End",   bg, "color_end")

    # ── Image element properties ──

    def _show_image_props(self, elem):
        src = elem.setdefault("source", {"category": "character", "index": 0})

        self._section("Source")
        self._add_combo("Category", src, "category", CATEGORIES)
        self._add_spin("Index", src, "index", 0, 99)

        self._section("Position")
        self._add_spin("X", elem, "x", -1000, 10000)
        self._add_spin("Y", elem, "y", -1000, 10000)

        self._section("Size")
        self._add_spin("Width",  elem, "width",  10, 5000)
        self._add_spin("Height", elem, "height", 10, 5000)

        self._section("Layout")
        self._add_combo("Anchor",   elem, "anchor",   ANCHORS)
        self._add_spin("Rotation",  elem, "rotation", -360, 360)

        self._section("Effects")
        effects = elem.setdefault("effects", {})

        # Outline toggle
        outline = effects.get("outline")
        has_ol = tk.BooleanVar(value=bool(outline))
        ttk.Checkbutton(self.prop_frame, text="Outline", variable=has_ol,
                        command=lambda: self._toggle_effect(elem, "outline", has_ol.get())
                        ).pack(fill="x", padx=8)
        if outline:
            self._add_color("  Color", outline, "color")
            self._add_spin("  Width", outline, "width", 1, 60)

        # Shadow toggle
        shadow = effects.get("shadow")
        has_sh = tk.BooleanVar(value=bool(shadow))
        ttk.Checkbutton(self.prop_frame, text="Shadow", variable=has_sh,
                        command=lambda: self._toggle_effect(elem, "shadow", has_sh.get())
                        ).pack(fill="x", padx=8, pady=(4, 0))
        if shadow:
            self._add_color("  Color", shadow, "color")
            self._add_spin("  Blur",  shadow, "blur", 0, 100)
            off = shadow.setdefault("offset", [10, 10])
            row = ttk.Frame(self.prop_frame)
            row.pack(fill="x", padx=4, pady=2)
            ttk.Label(row, text="  Offset", width=10).pack(side="left")
            self._add_inline_spin(row, "X:", off, 0, -200, 200)
            self._add_inline_spin(row, "Y:", off, 1, -200, 200)

    # ── Text element properties ──

    def _show_text_props(self, elem):
        self._section("Content")
        self._add_entry("Text", elem, "content")

        self._section("Position")
        self._add_spin("X", elem, "x", -1000, 10000)
        self._add_spin("Y", elem, "y", -1000, 10000)

        self._section("Typography")
        self._add_combo("Font",  elem, "font_family", FONT_FAMILIES)
        self._add_spin("Size",   elem, "font_size", 6, 500)
        self._add_color("Color", elem, "color")

        self._section("Layout")
        self._add_combo("Anchor",    elem, "anchor",    ANCHORS)
        self._add_combo("Align",     elem, "align",     ALIGNS)
        self._add_spin("Max Width",  elem, "max_width", 0, 5000)

    # ── Widget builders ──

    def _section(self, title):
        ttk.Label(self.prop_frame, text=title,
                  font=("Segoe UI", 9, "bold")).pack(fill="x", pady=(10, 2), padx=4)

    def _add_entry(self, label, obj, key):
        f = ttk.Frame(self.prop_frame);  f.pack(fill="x", padx=4, pady=2)
        ttk.Label(f, text=label, width=10).pack(side="left")
        var = tk.StringVar(value=str(obj.get(key, "")))
        ent = ttk.Entry(f, textvariable=var, width=22)
        ent.pack(side="left", fill="x", expand=True)

        def apply(*_):
            new = var.get()
            if obj.get(key) != new:
                self._push_undo()
                obj[key] = new
                self._refresh_canvas()
                self._refresh_element_list()

        ent.bind("<Return>",   apply)
        ent.bind("<FocusOut>", apply)

    def _add_spin(self, label, obj, key, lo, hi):
        f = ttk.Frame(self.prop_frame);  f.pack(fill="x", padx=4, pady=2)
        ttk.Label(f, text=label, width=10).pack(side="left")
        var = tk.IntVar(value=int(obj.get(key, 0)))
        spin = ttk.Spinbox(f, from_=lo, to=hi, textvariable=var, width=10)
        spin.pack(side="left")

        def apply(*_):
            try:
                v = int(var.get())
            except (ValueError, tk.TclError):
                return
            if obj.get(key) != v:
                self._push_undo()
                obj[key] = v
                self._refresh_canvas()

        spin.bind("<Return>",      apply)
        spin.bind("<FocusOut>",    apply)
        spin.bind("<<Increment>>", apply)
        spin.bind("<<Decrement>>", apply)

    def _add_inline_spin(self, parent, label, lst, idx, lo, hi):
        ttk.Label(parent, text=label).pack(side="left")
        var = tk.IntVar(value=int(lst[idx]))
        spin = ttk.Spinbox(parent, from_=lo, to=hi, textvariable=var, width=7)
        spin.pack(side="left", padx=(0, 8))

        def apply(*_):
            try:
                v = int(var.get())
            except (ValueError, tk.TclError):
                return
            if lst[idx] != v:
                self._push_undo()
                lst[idx] = v
                self._refresh_canvas()

        spin.bind("<Return>",      apply)
        spin.bind("<FocusOut>",    apply)
        spin.bind("<<Increment>>", apply)
        spin.bind("<<Decrement>>", apply)

    def _add_combo(self, label, obj, key, options):
        f = ttk.Frame(self.prop_frame);  f.pack(fill="x", padx=4, pady=2)
        ttk.Label(f, text=label, width=10).pack(side="left")
        var = tk.StringVar(value=str(obj.get(key, options[0])))
        cb = ttk.Combobox(f, textvariable=var, values=options, state="readonly", width=18)
        cb.pack(side="left")

        def apply(*_):
            new = var.get()
            if obj.get(key) != new:
                self._push_undo()
                obj[key] = new
                self._refresh_canvas()
                self._refresh_properties()     # some combos change which fields show

        cb.bind("<<ComboboxSelected>>", apply)

    def _add_color(self, label, obj, key):
        f = ttk.Frame(self.prop_frame);  f.pack(fill="x", padx=4, pady=2)
        ttk.Label(f, text=label, width=10).pack(side="left")

        cur = obj.get(key, "#000000")
        swatch = tk.Button(f, width=3, relief="solid", bd=1)
        try:
            swatch.config(bg=cur)
        except tk.TclError:
            swatch.config(bg="#000000")
        swatch.pack(side="left", padx=(0, 4))

        hex_var = tk.StringVar(value=cur)
        hex_ent = ttk.Entry(f, textvariable=hex_var, width=10)
        hex_ent.pack(side="left")

        def pick():
            res = colorchooser.askcolor(color=obj.get(key, "#000000"), title=f"Pick {label}")
            if res and res[1]:
                self._push_undo()
                obj[key] = res[1]
                swatch.config(bg=res[1])
                hex_var.set(res[1])
                self._refresh_canvas()

        def apply_hex(*_):
            val = hex_var.get().strip()
            if val and val.startswith("#") and len(val) in (4, 7, 9):
                if obj.get(key) != val:
                    self._push_undo()
                    obj[key] = val
                    try:
                        swatch.config(bg=val)
                    except tk.TclError:
                        pass
                    self._refresh_canvas()

        swatch.config(command=pick)
        hex_ent.bind("<Return>",   apply_hex)
        hex_ent.bind("<FocusOut>", apply_hex)

    def _toggle_effect(self, elem, effect, enabled):
        self._push_undo()
        effects = elem.setdefault("effects", {})
        if enabled:
            if effect == "outline":
                effects["outline"] = {"color": "#FFFFFF", "width": 5}
            elif effect == "shadow":
                effects["shadow"] = {"color": "#00000040", "offset": [10, 10], "blur": 10}
        else:
            effects.pop(effect, None)
            if not effects:
                elem.pop("effects", None)
        self._refresh_canvas()
        self._refresh_properties()

    # ═════════════════════════════════════════════════════════════════════════
    # Canvas interaction
    # ═════════════════════════════════════════════════════════════════════════

    def _hit_test(self, sx, sy):
        """Return the index of the topmost element under screen point, or None."""
        for i in range(len(self.template["elements"]) - 1, -1, -1):
            bbox = self.canvas.bbox(f"elem_{i}")
            if bbox and bbox[0] <= sx <= bbox[2] and bbox[1] <= sy <= bbox[3]:
                return i
        return None

    def _on_canvas_click(self, event):
        idx = self._hit_test(event.x, event.y)
        if idx is not None:
            self.selected_idx = idx
            elem = self.template["elements"][idx]
            self._drag_idx      = idx
            self._drag_start_sx = event.x
            self._drag_start_sy = event.y
            self._drag_orig_lx  = elem.get("x", 0)
            self._drag_orig_ly  = elem.get("y", 0)
            self._pre_drag_state = copy.deepcopy(self.template)
        else:
            self.selected_idx    = None
            self._drag_idx       = None
            self._pre_drag_state = None
        self._refresh_all()

    def _on_canvas_drag(self, event):
        if self._drag_idx is None:
            return
        dx = (event.x - self._drag_start_sx) / self.scale
        dy = (event.y - self._drag_start_sy) / self.scale
        elem = self.template["elements"][self._drag_idx]
        elem["x"] = int(self._drag_orig_lx + dx)
        elem["y"] = int(self._drag_orig_ly + dy)
        self._refresh_canvas()
        self._refresh_properties()

    def _on_canvas_release(self, event):
        if self._drag_idx is not None and self._pre_drag_state is not None:
            elem = self.template["elements"][self._drag_idx]
            if elem.get("x") != self._drag_orig_lx or elem.get("y") != self._drag_orig_ly:
                # Position changed — commit the pre-drag state as an undo snapshot
                self.undo_stack.append(self._pre_drag_state)
                self.redo_stack.clear()
                if len(self.undo_stack) > MAX_UNDO:
                    self.undo_stack.pop(0)
        self._drag_idx       = None
        self._pre_drag_state = None

    def _on_canvas_scroll(self, event):
        factor = 1.1 if event.delta > 0 else (1 / 1.1)
        self._zoom(factor)

    def _on_canvas_motion(self, event):
        lx, ly = self._to_logical(event.x, event.y)
        cw, ch = self.template["canvas_size"]
        if 0 <= lx <= cw and 0 <= ly <= ch:
            self.coord_lbl.config(text=f"x: {int(lx)}   y: {int(ly)}")
        else:
            self.coord_lbl.config(text="")

    def _deselect(self):
        self.selected_idx = None
        self._refresh_all()

    def _nudge(self, dx, dy):
        """Move the selected element by (dx, dy) logical pixels."""
        if self.selected_idx is None:
            return
        self._push_undo()
        elem = self.template["elements"][self.selected_idx]
        elem["x"] = elem.get("x", 0) + dx
        elem["y"] = elem.get("y", 0) + dy
        self._refresh_canvas()
        self._refresh_properties()

    # ═════════════════════════════════════════════════════════════════════════
    # Zoom
    # ═════════════════════════════════════════════════════════════════════════

    def _zoom(self, factor):
        self.scale = max(0.05, min(2.0, self.scale * factor))
        self.zoom_lbl.config(text=f"{int(self.scale * 100)} %")
        self._refresh_canvas()

    def _fit_zoom(self):
        cw, ch = self.template["canvas_size"]
        ww = max(self.canvas.winfo_width(), 200)
        wh = max(self.canvas.winfo_height(), 200)
        self.scale = min((ww - 40) / cw, (wh - 40) / ch)
        self.zoom_lbl.config(text=f"{int(self.scale * 100)} %")
        self._refresh_canvas()

    # ═════════════════════════════════════════════════════════════════════════
    # Element operations
    # ═════════════════════════════════════════════════════════════════════════

    def add_image_element(self):
        self._push_undo()
        cw, ch = self.template["canvas_size"]
        self.template["elements"].append({
            "type": "image",
            "source": {"category": "character", "index": 0},
            "x": cw // 2, "y": ch // 2,
            "width": 250, "height": 250,
            "anchor": "center",
        })
        self.selected_idx = len(self.template["elements"]) - 1
        self._refresh_all()

    def add_text_element(self):
        self._push_undo()
        cw, ch = self.template["canvas_size"]
        self.template["elements"].append({
            "type": "text",
            "content": "New Text",
            "x": cw // 2, "y": ch // 2,
            "font_family": "Outfit-Bold",
            "font_size": 60,
            "color": "#000000",
            "anchor": "center",
            "align": "center",
        })
        self.selected_idx = len(self.template["elements"]) - 1
        self._refresh_all()

    def delete_element(self):
        if self.selected_idx is None:
            return
        self._push_undo()
        del self.template["elements"][self.selected_idx]
        n = len(self.template["elements"])
        self.selected_idx = min(self.selected_idx, n - 1) if n else None
        self._refresh_all()

    def duplicate_element(self):
        if self.selected_idx is None:
            return
        self._push_undo()
        dup = copy.deepcopy(self.template["elements"][self.selected_idx])
        dup["x"] = dup.get("x", 0) + 30
        dup["y"] = dup.get("y", 0) + 30
        self.template["elements"].insert(self.selected_idx + 1, dup)
        self.selected_idx += 1
        self._refresh_all()

    def move_layer_up(self):
        """Move selected element UP one layer (later in the list = drawn on top)."""
        idx = self.selected_idx
        elems = self.template["elements"]
        if idx is None or idx >= len(elems) - 1:
            return
        self._push_undo()
        elems[idx], elems[idx + 1] = elems[idx + 1], elems[idx]
        self.selected_idx = idx + 1
        self._refresh_all()

    def move_layer_down(self):
        """Move selected element DOWN one layer (earlier in the list = drawn behind)."""
        idx = self.selected_idx
        elems = self.template["elements"]
        if idx is None or idx <= 0:
            return
        self._push_undo()
        elems[idx], elems[idx - 1] = elems[idx - 1], elems[idx]
        self.selected_idx = idx - 1
        self._refresh_all()

    # ═════════════════════════════════════════════════════════════════════════
    # File operations
    # ═════════════════════════════════════════════════════════════════════════

    def new_template(self):
        self.template     = self._default_template()
        self.current_file = None
        self.selected_idx = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._refresh_all()

    def open_template(self):
        init = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
        if not os.path.isdir(init):
            init = None
        path = filedialog.askopenfilename(
            title="Open Template JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
            initialdir=init,
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.template     = data
            self.current_file = path
            self.selected_idx = None
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._fit_zoom()
            self._refresh_all()
            self.status_lbl.config(text=f"Opened: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Open Error", f"Failed to load template:\n{exc}")

    def save_template(self):
        if self.current_file:
            self._write_json(self.current_file)
        else:
            self.save_as()

    def save_as(self):
        init = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
        if not os.path.isdir(init):
            init = None
        path = filedialog.asksaveasfilename(
            title="Save Template JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=init,
        )
        if path:
            self._write_json(path)

    def _write_json(self, path):
        try:
            export = self._clean_export(copy.deepcopy(self.template))
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(export, fh, indent=2)
            self.current_file = path
            self.status_lbl.config(text=f"Saved: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Save Error", f"Failed to save:\n{exc}")

    @staticmethod
    def _clean_export(data):
        """Strip zero-value optional fields so the exported JSON stays clean."""
        for elem in data.get("elements", []):
            if elem.get("rotation", 0) == 0:
                elem.pop("rotation", None)
            if elem.get("max_width", 0) == 0:
                elem.pop("max_width", None)
            eff = elem.get("effects", {})
            if not eff:
                elem.pop("effects", None)
        return data

    def load_theme(self):
        path = filedialog.askdirectory(title="Select Theme Folder")
        if not path:
            return
        self.theme_dir      = path
        self.indexed_images = self._scan_theme(path)
        parts = ", ".join(f"{k}: {len(v)}" for k, v in self.indexed_images.items())
        self.status_lbl.config(text=f"Theme loaded — {os.path.basename(path)}  ({parts})")
        self._refresh_canvas()

    @staticmethod
    def _scan_theme(theme_dir):
        """Mirror the logic in src/image_loader.py to index PNGs by category."""
        indexed = {}
        known = ["subcharacter", "character", "combo", "prop", "pattern", "scene"]
        for root, _dirs, files in os.walk(theme_dir):
            for fname in sorted(files):
                if not fname.lower().endswith(".png"):
                    continue
                full = os.path.join(root, fname)
                lower = fname.lower()
                cat = None
                for c in known:
                    if f"_{c}_" in lower:
                        cat = c
                        break
                if cat is None:
                    cat = os.path.basename(root).lower()
                indexed.setdefault(cat, []).append(full)
        for cat in indexed:
            indexed[cat].sort()
        return indexed

    # ═════════════════════════════════════════════════════════════════════════
    # Undo / Redo
    # ═════════════════════════════════════════════════════════════════════════

    def _push_undo(self):
        """Snapshot the current template state before a change."""
        self.undo_stack.append(copy.deepcopy(self.template))
        self.redo_stack.clear()
        if len(self.undo_stack) > MAX_UNDO:
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(copy.deepcopy(self.template))
        self.template = self.undo_stack.pop()
        self._clamp_selection()
        self._refresh_all()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(copy.deepcopy(self.template))
        self.template = self.redo_stack.pop()
        self._clamp_selection()
        self._refresh_all()

    def _clamp_selection(self):
        n = len(self.template["elements"])
        if self.selected_idx is not None:
            if n == 0:
                self.selected_idx = None
            elif self.selected_idx >= n:
                self.selected_idx = n - 1

    # ═════════════════════════════════════════════════════════════════════════
    # Status bar
    # ═════════════════════════════════════════════════════════════════════════

    def _update_status(self):
        name = self.template.get("name", "Untitled")
        n    = len(self.template["elements"])
        finfo = f"  —  {os.path.basename(self.current_file)}" if self.current_file else ""
        self.status_lbl.config(text=f"{name}{finfo}   |   {n} elements   |   {int(self.scale*100)} %")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    _app = TemplateEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
