#!/usr/bin/env python3
"""
Text Tools — Enhanced Dashboard (Tkinter)

- Editor: Input & Output with line numbers.
- Diff: Side-by-side Before(Input) | After(Output), line numbers, per-line and char-span highlights, synced scroll.
- Notes: Prompt writer; Replace/Insert into Input or Output.
- Right-click menu on all texts: Quick Paste, Paste, Copy, Cut, Select All, handy ops.
- Pretty JSON, snake_case, emoji cleanup, slash swap (\↔/).
- Live stats: Input/Output lines & chars (Diff header + Status bar).
- Text controls: toggle wrap for Input/Output/Notes.
- Snappy: debounced updates, gutters redraw only visible lines.

Deps: stdlib only.
"""

import os
import re
import json
import difflib
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font, messagebox
import tkinter.ttk as ttk
import sys

# --- THEMES AND STYLING ---
LIGHT_THEME = {
    "bg": "#f0f0f0",
    "fg": "#000000",
    "entry_bg": "#ffffff",
    "cursor": "#000000",
    "frame_bg": "#e0e0e0",
    "frame_fg": "#000000",
    "button_bg": "#dcdcdc", "button_fg": "#000000", "button_active_bg": "#c8c8c8",
    "danger_bg": "#f2dede", "danger_fg": "#a94442", "danger_active_bg": "#ebcccc",
    "success_bg": "#dff0d8", "success_fg": "#3c763d", "success_active_bg": "#d0e9c6",
    "primary_bg": "#d9edf7", "primary_fg": "#31708f", "primary_active_bg": "#c4e3f3",
    "status_bg": "#e7e7e7",
    "status_fg_success": "#3c763d",
    "status_fg_danger": "#a94442",
    "status_fg_info": "#31708f",
    "gutter_bg": "#e8e8e8",
    "gutter_fg": "#6b6b6b",
}

DARK_THEME = {
    "bg": "#2e2e2e",
    "fg": "#ffffff",
    "entry_bg": "#3e3e3e",
    "cursor": "#ffffff",
    "frame_bg": "#3c3c3c",
    "frame_fg": "#ffffff",
    "button_bg": "#5e5e5e", "button_fg": "#ffffff", "button_active_bg": "#6e6e6e",
    "danger_bg": "#a94442", "danger_fg": "#ffffff", "danger_active_bg": "#843534",
    "success_bg": "#3c763d", "success_fg": "#ffffff", "success_active_bg": "#2d572d",
    "primary_bg": "#31708f", "primary_fg": "#ffffff", "primary_active_bg": "#245269",
    "status_bg": "#252525",
    "status_fg_success": "#77dd77",
    "status_fg_danger": "#ff6961",
    "status_fg_info": "#aec6cf",
    "gutter_bg": "#2a2a2a",
    "gutter_fg": "#a0a0a0",
}

CONFIG_PATH = Path.home() / ".text_tools_config.json"

# --- REGEX PATTERNS ---
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)
_INVISIBLES_PATTERN = re.compile(r"[\u200D\u200C\uFE0E\uFE0F]")

IS_MAC = sys.platform == "darwin"

class TextToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Tools — Enhanced Dashboard")
        self.root.geometry("1280x820")
        self.root.minsize(980, 640)

        # state
        self.current_theme = DARK_THEME
        self.status_timer = None
        self.last_operation = None  # (callable, label)
        self._diff_job = None
        self._linenumber_canvases = []  # [(canvas, textwidget), ...]

        # fonts
        self.base_font = font.nametofont("TkTextFont").copy()
        self.base_font.configure(size=11)

        # load persisted config
        self._load_config()

        self._build_layout()
        self.apply_theme()
        self._bind_shortcuts()
        self._bind_change_events()
        self._update_stats()

    # -------------------- Layout --------------------
    def _build_layout(self):
        self.root.configure(bg=self.current_theme["bg"])

        # Paned window: left sidebar, right content
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg=self.current_theme["bg"])
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left sidebar (controls)
        self.sidebar = tk.Frame(self.paned, width=340, bg=self.current_theme["bg"])
        self.paned.add(self.sidebar)

        # Right content: Notebook with Editor / Diff / Notes
        self.right = tk.Frame(self.paned, bg=self.current_theme["bg"])
        self.paned.add(self.right)
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(1, weight=1)

        # --- Toolbar / Find bar ---
        self.find_bar = tk.Frame(self.right, height=32, bg=self.current_theme["bg"])
        self.find_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.find_bar.columnconfigure(1, weight=1)
        tk.Label(self.find_bar, text="Find:", bg=self.current_theme["bg"], fg=self.current_theme["fg"]).grid(row=0, column=0, sticky="w")
        self.find_var = tk.StringVar()
        self.find_entry = tk.Entry(self.find_bar, textvariable=self.find_var)
        self.find_entry.grid(row=0, column=1, sticky="ew", padx=6)
        self.find_match_case = tk.IntVar(value=0)
        tk.Checkbutton(self.find_bar, text="Match case", variable=self.find_match_case,
                       bg=self.current_theme["bg"], fg=self.current_theme["fg"], activebackground=self.current_theme["bg"]).grid(row=0, column=2, padx=(0, 6))
        tk.Button(self.find_bar, text="Prev", command=lambda: self._find(step=-1)).grid(row=0, column=3)
        tk.Button(self.find_bar, text="Next", command=lambda: self._find(step=+1)).grid(row=0, column=4, padx=(6, 0))
        tk.Button(self.find_bar, text="×", command=self._hide_find).grid(row=0, column=5, padx=(8, 0))
        self.find_bar.grid_remove()

        # --- Notebook ---
        self.nb = ttk.Notebook(self.right)
        self.nb.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # === Editor tab: Input (lined) over Output (lined) ===
        self.tab_editor = tk.Frame(self.nb, bg=self.current_theme["bg"])
        self.nb.add(self.tab_editor, text="Editor")
        vpaned = tk.PanedWindow(self.tab_editor, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg=self.current_theme["bg"])
        vpaned.pack(fill=tk.BOTH, expand=True)

        # Input area (lined)
        input_wrap = tk.Frame(vpaned, bg=self.current_theme["bg"])
        tk.Label(input_wrap, text="Input", bg=self.current_theme["bg"], fg=self.current_theme["fg"]).pack(anchor="w")
        self.input_frame = tk.Frame(input_wrap, bg=self.current_theme["bg"])
        self.input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.input_ln = tk.Canvas(self.input_frame, width=48, highlightthickness=0)
        self.input_ln.grid(row=0, column=0, sticky="ns")
        self.text_input = tk.Text(self.input_frame, height=12, undo=True, wrap="word", font=self.base_font)
        self.text_input.grid(row=0, column=1, sticky="nsew")
        self.in_vsb = tk.Scrollbar(self.input_frame, orient="vertical", command=lambda *a: (self.text_input.yview(*a), self._redraw_linenumbers(self.input_ln, self.text_input)))
        self.in_hsb = tk.Scrollbar(self.input_frame, orient="horizontal", command=self.text_input.xview)
        self.text_input.configure(yscrollcommand=lambda *a: (self.in_vsb.set(*a), self._redraw_linenumbers(self.input_ln, self.text_input)),
                                  xscrollcommand=self.in_hsb.set)
        self.input_frame.grid_columnconfigure(1, weight=1)
        self.input_frame.grid_rowconfigure(0, weight=1)
        self.in_vsb.grid(row=0, column=2, sticky="ns")
        self.in_hsb.grid(row=1, column=1, sticky="ew")
        vpaned.add(input_wrap)
        self._linenumber_canvases.append((self.input_ln, self.text_input))
        self._bind_text_defaults(self.text_input)

        # Output area (lined) + toolbar
        output_wrap = tk.Frame(vpaned, bg=self.current_theme["bg"])
        top_tools = tk.Frame(output_wrap, bg=self.current_theme["bg"])
        top_tools.pack(fill=tk.X)
        tk.Label(top_tools, text="Output", bg=self.current_theme["bg"], fg=self.current_theme["fg"]).pack(side=tk.LEFT)
        tk.Button(top_tools, text="Send Output → Input", command=self.send_output_to_input).pack(side=tk.RIGHT, padx=(6, 0))
        tk.Button(top_tools, text="Load File → Input", command=self.load_file_to_input).pack(side=tk.RIGHT, padx=(6, 0))

        self.output_frame = tk.Frame(output_wrap, bg=self.current_theme["bg"])
        self.output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_ln = tk.Canvas(self.output_frame, width=48, highlightthickness=0)
        self.output_ln.grid(row=0, column=0, sticky="ns")
        self.text_output = tk.Text(self.output_frame, height=12, undo=True, wrap="word", font=self.base_font)
        self.text_output.grid(row=0, column=1, sticky="nsew")
        self.out_vsb = tk.Scrollbar(self.output_frame, orient="vertical", command=lambda *a: (self.text_output.yview(*a), self._redraw_linenumbers(self.output_ln, self.text_output)))
        self.out_hsb = tk.Scrollbar(self.output_frame, orient="horizontal", command=self.text_output.xview)
        self.text_output.configure(yscrollcommand=lambda *a: (self.out_vsb.set(*a), self._redraw_linenumbers(self.output_ln, self.text_output)),
                                   xscrollcommand=self.out_hsb.set)
        self.output_frame.grid_columnconfigure(1, weight=1)
        self.output_frame.grid_rowconfigure(0, weight=1)
        self.out_vsb.grid(row=0, column=2, sticky="ns")
        self.out_hsb.grid(row=1, column=1, sticky="ew")
        vpaned.add(output_wrap)
        self._linenumber_canvases.append((self.output_ln, self.text_output))
        self._bind_text_defaults(self.text_output)

        # hide find bar now that editors exist
        self._hide_find()

        # === Diff tab: side-by-side (lined) ===
        self.tab_diff = tk.Frame(self.nb, bg=self.current_theme["bg"])
        self.nb.add(self.tab_diff, text="Diff")

        diff_header = tk.Frame(self.tab_diff, bg=self.current_theme["bg"])
        diff_header.pack(fill=tk.X, padx=8, pady=(8, 0))
        self.diff_stats = tk.Label(diff_header, text="Before: 0L/0C    After: 0L/0C", bg=self.current_theme["bg"], fg=self.current_theme["fg"])
        self.diff_stats.pack(side=tk.LEFT, padx=6)

        self.diff_pane = tk.PanedWindow(self.tab_diff, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg=self.current_theme["bg"])
        self.diff_pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Left (Before)
        left_wrap = tk.Frame(self.diff_pane, bg=self.current_theme["bg"])
        left_wrap.grid_columnconfigure(1, weight=1)
        left_wrap.grid_rowconfigure(0, weight=1)
        self.diff_left_ln = tk.Canvas(left_wrap, width=48, highlightthickness=0)
        self.diff_left_ln.grid(row=0, column=0, sticky="ns")
        self.diff_left = tk.Text(left_wrap, wrap="none", font=self.base_font, state="disabled")
        self.diff_left.grid(row=0, column=1, sticky="nsew")
        lscroll_y = tk.Scrollbar(left_wrap, orient="vertical", command=self._sync_scroll_y_left)
        lscroll_y.grid(row=0, column=2, sticky="ns")
        lscroll_x = tk.Scrollbar(left_wrap, orient="horizontal", command=self.diff_left.xview)
        lscroll_x.grid(row=1, column=1, sticky="ew")
        self.diff_left.configure(yscrollcommand=lambda *args: (self._sync_y(*args, which='left'), lscroll_y.set(*args), self._redraw_linenumbers(self.diff_left_ln, self.diff_left)),
                                 xscrollcommand=lscroll_x.set)
        self.diff_pane.add(left_wrap)
        self._linenumber_canvases.append((self.diff_left_ln, self.diff_left))
        self._bind_text_defaults(self.diff_left)

        # Right (After)
        right_wrap = tk.Frame(self.diff_pane, bg=self.current_theme["bg"])
        right_wrap.grid_columnconfigure(1, weight=1)
        right_wrap.grid_rowconfigure(0, weight=1)
        self.diff_right_ln = tk.Canvas(right_wrap, width=48, highlightthickness=0)
        self.diff_right_ln.grid(row=0, column=0, sticky="ns")
        self.diff_right = tk.Text(right_wrap, wrap="none", font=self.base_font, state="disabled")
        self.diff_right.grid(row=0, column=1, sticky="nsew")
        rscroll_y = tk.Scrollbar(right_wrap, orient="vertical", command=self._sync_scroll_y_right)
        rscroll_y.grid(row=0, column=2, sticky="ns")
        rscroll_x = tk.Scrollbar(right_wrap, orient="horizontal", command=self.diff_right.xview)
        rscroll_x.grid(row=1, column=1, sticky="ew")
        self.diff_right.configure(yscrollcommand=lambda *args: (self._sync_y(*args, which='right'), rscroll_y.set(*args), self._redraw_linenumbers(self.diff_right_ln, self.diff_right)),
                                  xscrollcommand=rscroll_x.set)
        self.diff_pane.add(right_wrap)
        self._linenumber_canvases.append((self.diff_right_ln, self.diff_right))
        self._bind_text_defaults(self.diff_right)

        # === Notes tab ===
        self.tab_notes = tk.Frame(self.nb, bg=self.current_theme["bg"])
        self.nb.add(self.tab_notes, text="Notes")
        notes_toolbar = tk.Frame(self.tab_notes, bg=self.current_theme["bg"])
        notes_toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))
        tk.Button(notes_toolbar, text="Replace Input", command=lambda: self._replace_widget(self.text_input, self._get_text(self.text_notes))).pack(side=tk.LEFT, padx=4)
        tk.Button(notes_toolbar, text="Replace Output", command=lambda: self._replace_widget(self.text_output, self._get_text(self.text_notes))).pack(side=tk.LEFT, padx=4)
        tk.Button(notes_toolbar, text="Insert → Input", command=lambda: self.text_input.insert(tk.INSERT, self._get_text(self.text_notes))).pack(side=tk.LEFT, padx=4)
        tk.Button(notes_toolbar, text="Insert → Output", command=lambda: self.text_output.insert(tk.INSERT, self._get_text(self.text_notes))).pack(side=tk.LEFT, padx=4)
        tk.Button(notes_toolbar, text="Save Notes…", command=lambda: self.save_text_from(self.text_notes)).pack(side=tk.RIGHT, padx=4)
        tk.Button(notes_toolbar, text="Load Notes…", command=self.load_notes).pack(side=tk.RIGHT, padx=4)
        self.notes_frame = tk.Frame(self.tab_notes, bg=self.current_theme["bg"])
        self.notes_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.notes_ln = tk.Canvas(self.notes_frame, width=48, highlightthickness=0)
        self.notes_ln.grid(row=0, column=0, sticky="ns")
        self.text_notes = tk.Text(self.notes_frame, height=20, undo=True, wrap="word", font=self.base_font)
        self.text_notes.grid(row=0, column=1, sticky="nsew")
        self.notes_vsb = tk.Scrollbar(self.notes_frame, orient="vertical", command=lambda *a: (self.text_notes.yview(*a), self._redraw_linenumbers(self.notes_ln, self.text_notes)))
        self.notes_hsb = tk.Scrollbar(self.notes_frame, orient="horizontal", command=self.text_notes.xview)
        self.text_notes.configure(yscrollcommand=lambda *a: (self.notes_vsb.set(*a), self._redraw_linenumbers(self.notes_ln, self.text_notes)),
                                  xscrollcommand=self.notes_hsb.set)
        self.notes_frame.grid_columnconfigure(1, weight=1)
        self.notes_frame.grid_rowconfigure(0, weight=1)
        self.notes_vsb.grid(row=0, column=2, sticky="ns")
        self.notes_hsb.grid(row=1, column=1, sticky="ew")
        self._linenumber_canvases.append((self.notes_ln, self.text_notes))
        self._bind_text_defaults(self.text_notes)

        # --- Status bar ---
        status_bar = tk.Frame(self.root, height=26, bg=self.current_theme["status_bg"])
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar.pack_propagate(False)
        self.status_label = tk.Label(status_bar, text="Ready", anchor="w", bg=self.current_theme["status_bg"], fg=self.current_theme["fg"])
        self.status_label.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        self.progress = ttk.Progressbar(status_bar, mode="indeterminate", length=120)
        self.progress.pack(side=tk.RIGHT, padx=8)

        # --- Sidebar content ---
        self._build_sidebar()
        self._configure_diff_tags()

    def _build_sidebar(self):
        s = self.sidebar
        for child in s.winfo_children():
            child.destroy()

        # Operations
        ops = tk.LabelFrame(s, text="Operations", padx=10, pady=10, bg=self.current_theme["bg"], fg=self.current_theme["fg"])
        ops.pack(fill=tk.X, padx=10, pady=(10, 10))

        self.buttons = {}
        self.buttons['pretty_json'] = tk.Button(ops, text="Pretty-print JSON", command=self._wrap_op(self.process_pretty_json, "pretty_json"))
        self.buttons['php_json']    = tk.Button(ops, text="PHP Serialized → JSON", command=self._wrap_op(self.process_php_to_json, "PHP→JSON"))
        self.buttons['snake']       = tk.Button(ops, text="Convert to snake_case", command=self._wrap_op(self.process_snake_case, "snake_case"))
        self.buttons['emoji']       = tk.Button(ops, text="Clean Emojis & Text", command=self._wrap_op(self.process_remove_emojis, "clean_emojis"))
        self.buttons['slash_fw']    = tk.Button(ops, text=r"Swap \ → /", command=self._wrap_op(lambda: self.swap_slashes('to_forward'), "swap_slashes_fw"))
        self.buttons['slash_bw']    = tk.Button(ops, text=r"Swap / → \ ", command=self._wrap_op(lambda: self.swap_slashes('to_back'), "swap_slashes_bw"))
        for key in ['pretty_json', 'php_json', 'snake', 'emoji', 'slash_fw', 'slash_bw']:
            self.buttons[key].pack(fill=tk.X, pady=4)

        # Output & State
        out = tk.LabelFrame(s, text="Output & State", padx=10, pady=10, bg=self.current_theme["bg"], fg=self.current_theme["fg"])
        out.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(out, text="Copy Output", command=self.copy_to_clipboard).pack(fill=tk.X, pady=4)
        tk.Button(out, text="Save Input…", command=lambda: self.save_text_from(self.text_input)).pack(fill=tk.X, pady=4)
        tk.Button(out, text="Save Output…", command=lambda: self.save_text_from(self.text_output)).pack(fill=tk.X, pady=4)
        tk.Button(out, text="Save Notes…", command=lambda: self.save_text_from(self.text_notes)).pack(fill=tk.X, pady=4)
        tk.Button(out, text="Reset UI", command=self.reset_ui).pack(fill=tk.X, pady=4)

        # Text Controls
        tctrl = tk.LabelFrame(s, text="Text Controls", padx=10, pady=10, bg=self.current_theme["bg"], fg=self.current_theme["fg"])
        tctrl.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.wrap_in = tk.BooleanVar(value=True)
        self.wrap_out = tk.BooleanVar(value=True)
        self.wrap_notes = tk.BooleanVar(value=True)
        tk.Checkbutton(tctrl, text="Wrap Input", variable=self.wrap_in, bg=self.current_theme["bg"], fg=self.current_theme["fg"],
                       command=lambda: self._set_wrap(self.text_input, self.wrap_in.get())).pack(anchor="w")
        tk.Checkbutton(tctrl, text="Wrap Output", variable=self.wrap_out, bg=self.current_theme["bg"], fg=self.current_theme["fg"],
                       command=lambda: self._set_wrap(self.text_output, self.wrap_out.get())).pack(anchor="w")
        tk.Checkbutton(tctrl, text="Wrap Notes", variable=self.wrap_notes, bg=self.current_theme["bg"], fg=self.current_theme["fg"],
                       command=lambda: self._set_wrap(self.text_notes, self.wrap_notes.get())).pack(anchor="w")

        # Settings (bottom)
        settings = tk.LabelFrame(s, text="Settings", padx=10, pady=10, bg=self.current_theme["bg"], fg=self.current_theme["fg"])
        settings.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(settings, text="Toggle Theme", command=self.toggle_theme).pack(fill=tk.X)

    # -------------------- Helpers: line numbers & context menu --------------------
    def _bind_text_defaults(self, widget: tk.Text):
        # Right-click context menu
        self._attach_context_menu(widget)
        # Line number redraws
        widget.bind("<KeyRelease>", lambda e, w=widget: self._schedule_lnr_redraw(w))
        widget.bind("<MouseWheel>", lambda e, w=widget: (self._schedule_lnr_redraw(w), None))
        widget.bind("<Button-4>",   lambda e, w=widget: (self._schedule_lnr_redraw(w), None))  # Linux
        widget.bind("<Button-5>",   lambda e, w=widget: (self._schedule_lnr_redraw(w), None))
        widget.bind("<<Change>>",   lambda e, w=widget: self._schedule_lnr_redraw(w))
        widget.bind("<Configure>",  lambda e, w=widget: self._schedule_lnr_redraw(w))

    def _schedule_lnr_redraw(self, widget):
        for canvas, tw in self._linenumber_canvases:
            if tw is widget:
                self._redraw_linenumbers(canvas, tw)
                break

    def _redraw_linenumbers(self, canvas: tk.Canvas, text: tk.Text):
        theme = self.current_theme
        canvas.delete("all")
        canvas.configure(bg=theme["gutter_bg"])
        i = text.index("@0,0")
        while True:
            d = text.dlineinfo(i)
            if d is None:
                break
            y = d[1]
            linenum = str(i).split('.')[0]
            canvas.create_text(2, y, anchor='nw', text=linenum, fill=theme["gutter_fg"])
            i = text.index(f"{i}+1line")

    def _attach_context_menu(self, widget: tk.Text):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Quick Paste", command=lambda w=widget: self._quick_paste(w))
        menu.add_command(label="Paste", command=lambda w=widget: w.event_generate("<<Paste>>"))
        menu.add_command(label="Copy", command=lambda w=widget: w.event_generate("<<Copy>>"))
        menu.add_command(label="Cut", command=lambda w=widget: w.event_generate("<<Cut>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda w=widget: (w.tag_add("sel", "1.0", "end-1c"), w.focus_set()))
        menu.add_separator()
        menu.add_command(label="Pretty JSON → Output", command=self._wrap_op(self.process_pretty_json, "pretty_json"))
        menu.add_command(label=r"Swap \ → /  (focused)", command=self._wrap_op(lambda: self.swap_slashes('to_forward'), "swap_slashes_fw"))
        menu.add_command(label=r"Swap / → \  (focused)", command=self._wrap_op(lambda: self.swap_slashes('to_back'), "swap_slashes_bw"))

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        btn = "<Button-2>" if IS_MAC else "<Button-3>"
        widget.bind(btn, show_menu)

    def _quick_paste(self, widget: tk.Text):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            self.show_status_message("Clipboard empty.", "info"); return
        try:
            widget.insert(tk.INSERT, text)
            self.show_status_message("Pasted.", "success")
        finally:
            self._update_diff()
            self._update_stats()

    # -------------------- Theming --------------------
    def apply_theme(self):
        theme = self.current_theme
        self.root.configure(bg=theme["bg"])

        def apply_to_children(widget):
            cls = widget.winfo_class()
            if cls in ('Frame', 'TFrame'):
                widget.configure(bg=theme["bg"])
            elif cls in ('Label', 'TLabel'):
                try: widget.configure(bg=theme["bg"], fg=theme["fg"])
                except tk.TclError: pass
            elif cls in ('Labelframe', 'TLabelframe'):
                try: widget.configure(bg=theme["bg"], fg=theme["fg"])
                except tk.TclError: pass
                for child in widget.winfo_children():
                    if child.winfo_class() == 'Frame':
                        child.configure(bg=theme["bg"])
            for child in widget.winfo_children():
                apply_to_children(child)

        apply_to_children(self.root)

        for w in (self.text_input, self.text_output, self.diff_left, self.diff_right, self.text_notes):
            try:
                w.configure(
                    bg=theme["entry_bg"], fg=theme["fg"],
                    insertbackground=theme["cursor"],
                    selectbackground=theme["primary_bg"],
                    selectforeground=theme["primary_fg"],
                )
            except tk.TclError:
                pass

        if hasattr(self, 'status_label'):
            self.status_label.master.configure(bg=theme["status_bg"])
            self.status_label.configure(bg=theme["status_bg"], fg=theme["fg"])

        for name in ('text_input', 'text_output'):
            getattr(self, name).tag_configure('search_hit', background=theme["primary_bg"], foreground=theme["primary_fg"])

        # Diff tags
        self._configure_diff_tags()

        # Redraw gutters with new colors
        for canvas, tw in self._linenumber_canvases:
            self._redraw_linenumbers(canvas, tw)

    def _configure_diff_tags(self):
        for widget in (self.diff_left, self.diff_right):
            try:
                widget.tag_configure('line_add', background=self.current_theme["success_bg"])
                widget.tag_configure('line_del', background=self.current_theme["danger_bg"])
                widget.tag_configure('line_rep', background=self.current_theme["primary_bg"], foreground=self.current_theme["primary_fg"])
                widget.tag_configure('char_add', underline=True)
                widget.tag_configure('char_del', underline=True)
                widget.tag_configure('char_rep', underline=True)
            except tk.TclError:
                pass

    # -------------------- Status & Busy --------------------
    def show_status_message(self, text, msg_type="info", duration_ms=3500):
        if hasattr(self, 'status_timer') and self.status_timer:
            self.root.after_cancel(self.status_timer)
        fg_color = self.current_theme.get(f"status_fg_{msg_type}", self.current_theme["fg"])
        self.status_label.config(text=text, fg=fg_color)
        self.status_timer = self.root.after(duration_ms, self._clear_status_message)

    def _clear_status_message(self):
        self.status_label.config(text="Ready", fg=self.current_theme["fg"])
        self.status_timer = None

    @contextmanager
    def busy(self, message: str = "Working…"):
        try: self.progress.start(12)
        except Exception: pass
        self.show_status_message(message, "info", duration_ms=10_000)
        self.root.update_idletasks()
        try:
            yield
        finally:
            try: self.progress.stop()
            except Exception: pass
            self.show_status_message("Done", "success")

    # -------------------- Shortcuts & Change Events --------------------
    def _bind_shortcuts(self):
        self.root.bind("<Control-f>", self._show_find)
        self.root.bind("<Escape>", self._hide_find)
        self.root.bind("<Control-slash>", lambda e: self.toggle_theme())
        self.root.bind("<Control-s>", lambda e: self.save_text_from(self.text_output))  # save Output by default
        self.root.bind("<Control-b>", lambda e: self.copy_to_clipboard())
        self.root.bind("<Control-=>", lambda e: self._zoom(+1))
        self.root.bind("<Control-plus>", lambda e: self._zoom(+1))
        self.root.bind("<Control-minus>", lambda e: self._zoom(-1))
        self.root.bind("<F5>", lambda e: self._rerun_last())
        self.root.bind("<Control-Key-1>", lambda e: self._wrap_op(self.process_php_to_json, "PHP→JSON")())
        self.root.bind("<Control-Key-2>", lambda e: self._wrap_op(self.process_snake_case, "snake_case")())
        self.root.bind("<Control-Key-3>", lambda e: self._wrap_op(self.process_remove_emojis, "clean_emojis")())
        self.root.bind("<Control-Key-4>", lambda e: self._wrap_op(self.process_pretty_json, "pretty_json")())
        self.root.bind("<Control-r>",   lambda e: self.reset_ui())

        # sync wheel on diff panes
        for w in (self.diff_left, self.diff_right):
            w.bind("<MouseWheel>", self._on_mousewheel)
            w.bind("<Button-4>", self._on_mousewheel)  # Linux
            w.bind("<Button-5>", self._on_mousewheel)

    def _bind_change_events(self):
        self.text_input.bind('<<Modified>>', self._on_text_modified)
        self.text_output.bind('<<Modified>>', self._on_text_modified)
        self.text_notes.bind('<<Modified>>', self._on_text_modified)

    def _on_text_modified(self, event):
        w = event.widget
        try: w.edit_modified(False)
        except tk.TclError: pass
        if self._diff_job:
            self.root.after_cancel(self._diff_job)
        self._diff_job = self.root.after(120, lambda: (self._update_diff(), self._update_stats()))

    # -------------------- Find --------------------
    def _show_find(self, *_):
        self.find_bar.grid()
        self.find_entry.focus_set()
        self.find_entry.select_range(0, tk.END)

    def _hide_find(self, *_):
        try: self.find_bar.grid_remove()
        except Exception: pass
        for w in (self.text_input, self.text_output):
            w.tag_remove('search_hit', '1.0', tk.END)

    def _find(self, step=+1):
        pattern = self.find_var.get()
        if not pattern:
            return
        widget = self.root.focus_get()
        if widget not in (self.text_input, self.text_output, self.text_notes):
            widget = self.text_input

        widget.tag_remove('search_hit', '1.0', tk.END)
        start = '1.0'; hits = []
        nocase = 0 if self.find_match_case.get() else 1
        while True:
            idx = widget.search(pattern, start, nocase=nocase, stopindex=tk.END)
            if not idx: break
            end = f"{idx}+{len(pattern)}c"
            widget.tag_add('search_hit', idx, end)
            hits.append(idx)
            start = end
        if not hits:
            self.show_status_message("No matches", "info"); return

        cur = widget.index(tk.INSERT)
        positions = [widget.index(h) for h in hits]
        target = (next((p for p in positions if p > cur), positions[0]) if step > 0
                  else next((p for p in reversed(positions) if p < cur), list(reversed(positions))[0]))
        widget.mark_set(tk.INSERT, target); widget.see(target)

    # -------------------- Persistence --------------------
    def _load_config(self):
        if CONFIG_PATH.exists():
            try:
                cfg = json.loads(CONFIG_PATH.read_text("utf-8"))
                self.current_theme = LIGHT_THEME if cfg.get("theme") == "light" else DARK_THEME
                size = int(cfg.get("font_size", 11)); self.base_font.configure(size=size)
            except Exception:
                pass

    def _save_config(self):
        data = {
            "theme": "light" if self.current_theme == LIGHT_THEME else "dark",
            "font_size": self.base_font.actual("size"),
        }
        try:
            CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    # -------------------- IO helpers & stats --------------------
    def get_source_text_widget(self):
        focused_widget = self.root.focus_get()
        if focused_widget in (self.text_input, self.text_output, self.text_notes):
            return focused_widget
        if self._get_text(self.text_output).strip():
            return self.text_output
        return self.text_input

    def _get_text(self, widget):
        return widget.get("1.0", "end-1c")

    def _replace_widget(self, widget, text):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        self._update_diff(); self._update_stats()

    def write_to_output(self, text: str):
        self._replace_widget(self.text_output, text)
        self.show_status_message("Output updated.", "success")

    def send_output_to_input(self):
        self._replace_widget(self.text_input, self._get_text(self.text_output))
        self.show_status_message("Output moved to Input", "info")

    def load_file_to_input(self):
        path = filedialog.askopenfilename(filetypes=[("Text/JSON", "*.txt *.json *.log *.md"), ("All Files", "*.*")])
        if not path: return
        try:
            data = Path(path).read_text(encoding="utf-8")
            self._replace_widget(self.text_input, data)
            self.show_status_message(f"Loaded {os.path.basename(path)}", "success")
        except Exception as e:
            self.show_status_message(f"Error loading file: {e}", "danger")

    def _set_wrap(self, widget: tk.Text, wrap_on: bool):
        widget.configure(wrap=("word" if wrap_on else "none"))
        self._update_diff(); self._update_stats()

    def _update_stats(self):
        in_txt = self._get_text(self.text_input)
        out_txt = self._get_text(self.text_output)
        in_lines = in_txt.count("\n") + (1 if in_txt else 0)
        out_lines = out_txt.count("\n") + (1 if out_txt else 0)
        in_chars = len(in_txt); out_chars = len(out_txt)
        self.diff_stats.configure(text=f"Before: {in_lines}L / {in_chars}C    After: {out_lines}L / {out_chars}C")
        self.status_label.configure(text=f"Input: {in_lines}L/{in_chars}C    |    Output: {out_lines}L/{out_chars}C")

    # -------------------- Diff (side-by-side) --------------------
    def _update_diff(self):
        left_lines = self._get_text(self.text_input).splitlines()
        right_lines = self._get_text(self.text_output).splitlines()

        sm = difflib.SequenceMatcher(a=left_lines, b=right_lines)
        pairs = []  # (left_line, right_line, tag)

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    pairs.append((left_lines[i1 + k], right_lines[j1 + k], "equal"))
            elif tag == "replace":
                n = max(i2 - i1, j2 - j1)
                for k in range(n):
                    l = left_lines[i1 + k] if k < (i2 - i1) else ""
                    r = right_lines[j1 + k] if k < (j2 - j1) else ""
                    pairs.append((l, r, "replace"))
            elif tag == "delete":
                for k in range(i2 - i1):
                    pairs.append((left_lines[i1 + k], "", "delete"))
            elif tag == "insert":
                for k in range(j2 - j1):
                    pairs.append(("", right_lines[j1 + k], "insert"))

        self.diff_left.configure(state="normal"); self.diff_right.configure(state="normal")
        self.diff_left.delete("1.0", tk.END);     self.diff_right.delete("1.0", tk.END)

        for idx, (l, r, tag) in enumerate(pairs, start=1):
            l_start = f"{idx}.0"; r_start = f"{idx}.0"
            self.diff_left.insert(tk.END, l + "\n")
            self.diff_right.insert(tk.END, r + "\n")
            if tag == "delete":
                self.diff_left.tag_add("line_del", l_start, f"{idx}.end")
            elif tag == "insert":
                self.diff_right.tag_add("line_add", r_start, f"{idx}.end")
            elif tag == "replace":
                self.diff_left.tag_add("line_rep", l_start, f"{idx}.end")
                self.diff_right.tag_add("line_rep", r_start, f"{idx}.end")
                self._highlight_char_diffs(idx, l, r)

        self.diff_left.configure(state="disabled"); self.diff_right.configure(state="disabled")
        # refresh line numbers for diff
        self._redraw_linenumbers(self.diff_left_ln, self.diff_left)
        self._redraw_linenumbers(self.diff_right_ln, self.diff_right)

    def _highlight_char_diffs(self, line_no: int, left: str, right: str):
        sm = difflib.SequenceMatcher(a=left, b=right)
        for tag, a1, a2, b1, b2 in sm.get_opcodes():
            if tag == "equal": continue
            if a1 != a2:
                self.diff_left.tag_add("char_del" if tag == "delete" else "char_rep", f"{line_no}.{a1}", f"{line_no}.{a2}")
            if b1 != b2:
                self.diff_right.tag_add("char_add" if tag == "insert" else "char_rep", f"{line_no}.{b1}", f"{line_no}.{b2}")

    # --- diff scrolling sync ---
    def _sync_y(self, *args, which='left'):
        if which == 'left':
            self.diff_right.yview_moveto(args[0])
        else:
            self.diff_left.yview_moveto(args[0])

    def _sync_scroll_y_left(self, *args):
        self.diff_left.yview(*args)
        self.diff_right.yview_moveto(self.diff_left.yview()[0])
        self._redraw_linenumbers(self.diff_left_ln, self.diff_left)
        self._redraw_linenumbers(self.diff_right_ln, self.diff_right)

    def _sync_scroll_y_right(self, *args):
        self.diff_right.yview(*args)
        self.diff_left.yview_moveto(self.diff_right.yview()[0])
        self._redraw_linenumbers(self.diff_left_ln, self.diff_left)
        self._redraw_linenumbers(self.diff_right_ln, self.diff_right)

    def _on_mousewheel(self, event):
        delta = 0
        if event.num == 5 or event.delta < 0: delta = 1
        elif event.num == 4 or event.delta > 0: delta = -1
        self.diff_left.yview_scroll(delta, "units")
        self.diff_right.yview_scroll(delta, "units")
        self._redraw_linenumbers(self.diff_left_ln, self.diff_left)
        self._redraw_linenumbers(self.diff_right_ln, self.diff_right)
        return "break"

    # -------------------- Shortcuts helpers --------------------
    def _zoom(self, delta: int):
        size = max(8, self.base_font.actual("size") + delta)
        self.base_font.configure(size=size)
        for w in (self.text_input, self.text_output, self.diff_left, self.diff_right, self.text_notes):
            w.configure(font=self.base_font)
        self._save_config()
        # re-draw gutters (font metrics changed)
        for canvas, tw in self._linenumber_canvases:
            self._redraw_linenumbers(canvas, tw)

    def _rerun_last(self):
        if self.last_operation:
            func, label = self.last_operation
            func()
            self.show_status_message(f"Re-ran: {label}", "info")

    def _wrap_op(self, fn, label):
        def inner():
            self.last_operation = (inner, label)
            with self.busy(f"Running {label}…"):
                fn()
        return inner

    # -------------------- Processing --------------------
    @staticmethod
    def to_snake_token(s: str) -> str:
        s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
        return s.strip('_').lower()

    @staticmethod
    def snake_case_text(text: str) -> str:
        try:
            obj = json.loads(text)
            def snake_keys(x):
                if isinstance(x, dict):
                    return {TextToolsApp.to_snake_token(k): snake_keys(v) for k, v in x.items()}
                if isinstance(x, list):
                    return [snake_keys(i) for i in x]
                return x
            return json.dumps(snake_keys(obj), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        lines = text.splitlines()
        return "\n".join(TextToolsApp.to_snake_token(ln) if ln.strip() else ln for ln in lines)

    @staticmethod
    def remove_emojis(text: str) -> str:
        text = _EMOJI_PATTERN.sub("", text)
        text = _INVISIBLES_PATTERN.sub("", text)
        return text

    @staticmethod
    def normalize_after_removal(text: str) -> str:
        processed_lines = []
        hr_pattern = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
        for line in text.splitlines():
            if hr_pattern.match(line):
                processed_lines.append(line); continue
            line = line.replace("\u00A0", " ")
            line = re.sub(r"[\u2010-\u2015\u2212]", " - ", line)
            line = re.sub(r"([\(\[\{])\s+", r"\1", line)
            line = re.sub(r"\s+([\)\]\}])", r"\1", line)
            line = re.sub(r"[\(\[\{]\s*[\)\]\}]", "", line)
            line = re.sub(r"\s+([,.;:!?])", r"\1", line)
            line = re.sub(r"[ \t\f\v]+", " ", line)
            processed_lines.append(line.rstrip())
        return "\n".join(processed_lines)

    # Commands
    def process_php_to_json(self):
        input_text = self._get_text(self.text_input)
        pattern = r's:\d+:"(.*?)";s:\d+:"(.*?)";'
        matches = re.findall(pattern, input_text)
        data_dict = {k: v for k, v in matches if not any(x in k or x in v for x in ['\";', 'a:', 'i:', 'b:', 'N'])}
        json_output = json.dumps(data_dict, indent=2, ensure_ascii=False)
        self.write_to_output(json_output)
        self.show_status_message(f"Converted {len(data_dict)} key-value pairs.", "success")

    def process_snake_case(self):
        src = self.get_source_text_widget()
        raw_text = self._get_text(src)
        result = self.snake_case_text(raw_text)
        self.write_to_output(result)
        self.show_status_message("Text converted to snake_case.", "success")

    def process_remove_emojis(self):
        src = self.get_source_text_widget()
        raw_text = self._get_text(src)
        cleaned = self.remove_emojis(raw_text)
        normalized = self.normalize_after_removal(cleaned)
        self.write_to_output(normalized)
        self.show_status_message("Emojis removed and text normalized.", "success")

    def process_pretty_json(self):
        src = self.get_source_text_widget()
        raw = self._get_text(src)
        try:
            obj = json.loads(raw)
        except Exception as e:
            self.show_status_message(f"JSON parse error: {e}", "danger"); return
        self.write_to_output(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True))
        self.show_status_message("Pretty-printed JSON.", "success")

    def swap_slashes(self, direction='to_forward'):
        src = self.get_source_text_widget()
        try:
            sel_start = src.index("sel.first"); sel_end = src.index("sel.last")
            text = src.get(sel_start, sel_end); use_sel = True
        except tk.TclError:
            sel_start = "1.0"; sel_end = tk.END
            text = src.get(sel_start, sel_end); use_sel = False

        replaced = text.replace("\\", "/") if direction == 'to_forward' else text.replace("/", "\\")
        if use_sel: src.delete(sel_start, sel_end); src.insert(sel_start, replaced)
        else:       src.delete("1.0", tk.END);       src.insert("1.0", replaced)
        self._update_diff(); self._update_stats()
        self.show_status_message("Slash swap applied.", "success")

    # Clipboard / Files / Notes / Reset
    def copy_to_clipboard(self):
        output_text = self._get_text(self.text_output)
        if output_text.strip():
            self.root.clipboard_clear(); self.root.clipboard_append(output_text)
            self.show_status_message("Output copied to clipboard.", "info")
        else:
            self.show_status_message("Output is empty, nothing to copy.", "danger")

    def save_text_from(self, widget):
        text = self._get_text(widget)
        if not text.strip():
            self.show_status_message("Nothing to save.", "danger"); return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = filedialog.asksaveasfilename(
            initialfile=f"export_{ts}.txt",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("JSON", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                Path(filepath).write_text(text, encoding="utf-8")
                self.show_status_message(f"Saved to {filepath}", "success")
            except Exception as e:
                self.show_status_message(f"Error saving file: {e}", "danger")

    def load_notes(self):
        path = filedialog.askopenfilename(filetypes=[("Text/JSON/MD", "*.txt *.json *.md"), ("All Files", "*.*")])
        if not path: return
        try:
            self._replace_widget(self.text_notes, Path(path).read_text(encoding="utf-8"))
            self.show_status_message(f"Notes loaded: {os.path.basename(path)}", "success")
        except Exception as e:
            messagebox.showerror("Load Notes Error", str(e))

    def reset_ui(self):
        for w in (self.text_input, self.text_output, self.text_notes):
            w.delete("1.0", tk.END)
        for w in (self.diff_left, self.diff_right):
            w.configure(state="normal"); w.delete("1.0", tk.END); w.configure(state="disabled")
        self.find_var.set(""); self._hide_find()
        self._update_diff(); self._update_stats()
        self.show_status_message("UI reset.", "info")

    # -------------------- Theme toggle --------------------
    def toggle_theme(self):
        self.current_theme = DARK_THEME if self.current_theme == LIGHT_THEME else LIGHT_THEME
        self.apply_theme()
        self._save_config()
        self.show_status_message("Theme changed", "info")


# -------------------- Entrypoint --------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = TextToolsApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app._save_config(), root.destroy()))
    root.mainloop()
