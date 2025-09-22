#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import html
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ================== Core parser (kept intact) ==================

LENIENT_STRING_TERMINATOR = False
WARNINGS = []

def _reset_warnings():
    WARNINGS.clear()

def _warn(kind: str, **data):
    WARNINGS.append({"kind": kind, **data})

class ParseError(Exception):
    def __init__(self, message: str, pos: int):
        super().__init__(message)
        self.pos = pos

def _read_until(b: bytes, i: int, delim: bytes):
    j = b.find(delim, i)
    if j == -1:
        raise ParseError("Unexpected end: delimiter not found", i)
    return b[i:j], j + len(delim)

def _parse_int(b: bytes, i: int):
    num, i = _read_until(b, i, b';')
    try:
        return int(num), i
    except Exception:
        raise ParseError(f"Invalid integer: {num!r}", i)

def _parse_float(b: bytes, i: int):
    num, i = _read_until(b, i, b';')
    try:
        return float(num), i
    except Exception:
        raise ParseError(f"Invalid float: {num!r}", i)

def _parse_bool(b: bytes, i: int):
    if b[i:i+2] not in (b'0;', b'1;'):
        raise ParseError("Invalid boolean token (expected 0; or 1;)", i)
    return (b[i:i+1] == b'1'), i + 2

def _decode_bytes(sbytes: bytes) -> str:
    try:
        return sbytes.decode('utf-8')
    except UnicodeDecodeError:
        return sbytes.decode('latin-1')

def _lenient_scan_close(b: bytes, start: int):
    MAX_LOOKAHEAD = 1_000_000
    end_limit = min(len(b), start + MAX_LOOKAHEAD)
    k = start
    while True:
        k = b.find(b'"', k, end_limit)
        if k == -1:
            return None, None
        j = k + 1
        while j < len(b) and b[j] in b' \t\r\n':
            j += 1
        if j < len(b) and b[j:j+1] == b';':
            sbytes = b[start:k]
            return sbytes, j + 1
        k += 1

def _parse_string(b: bytes, i: int):
    global LENIENT_STRING_TERMINATOR
    strlen_bytes, i = _read_until(b, i, b':')
    try:
        strlen = int(strlen_bytes)
    except Exception:
        raise ParseError(f"Invalid string length: {strlen_bytes!r}", i)
    if b[i:i+1] != b'"':
        raise ParseError('Expected opening quote for string', i)
    i += 1
    start = i
    end_expected = start + strlen
    if len(b) - start < strlen:
        if not LENIENT_STRING_TERMINATOR:
            raise ParseError('String length mismatch vs s:<len> (too short)', i)
        sbytes, i_new = _lenient_scan_close(b, start)
        if sbytes is None:
            raise ParseError('String length mismatch and no viable closing found', i)
        _warn("string_length_repair_short", at_byte=start, declared_length=int(strlen), actual_length=int(len(sbytes)))
        return _decode_bytes(sbytes), i_new
    sbytes = b[start:end_expected]
    i = end_expected
    if b[i:i+1] == b'"':
        i += 1
        while i < len(b) and b[i] in b' \t\r\n':
            i += 1
        if b[i:i+1] == b';':
            i += 1
            return _decode_bytes(sbytes), i
    if LENIENT_STRING_TERMINATOR:
        sbytes2, i_new = _lenient_scan_close(b, start)
        if sbytes2 is None:
            raise ParseError('Expected closing "\";" for string', i)
        if len(sbytes2) != strlen:
            _warn("string_length_repair_mismatch", at_byte=start, declared_length=int(strlen), actual_length=int(len(sbytes2)))
        return _decode_bytes(sbytes2), i_new
    raise ParseError('Expected closing "\";" for string', i)

def _parse_key(b: bytes, i: int):
    t = b[i:i+2]
    if t == b'i:':
        return _parse_int(b, i+2)
    elif t == b's:':
        return _parse_string(b, i+2)
    else:
        raise ParseError(f'Unsupported key type: {t!r}', i)

def _parse_value(b: bytes, i: int):
    t = b[i:i+2]
    if t == b's:':
        return _parse_string(b, i+2)
    if t == b'i:':
        return _parse_int(b, i+2)
    if t == b'd:':
        return _parse_float(b, i+2)
    if t == b'b:':
        return _parse_bool(b, i+2)
    if b[i:i+2] == b'N;':
        return None, i + 2
    if t == b'a:':
        i += 2
        count_bytes, i = _read_until(b, i, b':')
        try:
            count = int(count_bytes)
        except Exception:
            raise ParseError(f"Invalid array count: {count_bytes!r}", i)
        if b[i:i+1] != b'{':
            raise ParseError('Expected "{" after array length', i)
        i += 1
        items = []
        for _ in range(count):
            k, i = _parse_key(b, i)
            v, i = _parse_value(b, i)
            items.append((k, v))
        if b[i:i+1] != b'}':
            raise ParseError('Expected "}" to close array', i)
        i += 1
        keys = [k for k, _ in items]
        if keys and all(isinstance(k, int) for k in keys) and keys == list(range(len(keys))):
            return [v for _, v in items], i
        else:
            d = {}
            for k, v in items:
                d[k] = v
            return d, i
    raise ParseError(f'Unsupported value type: {b[i:i+10]!r}', i)

def php_unserialize(serialized: str):
    _reset_warnings()
    b = serialized.encode('utf-8', errors='surrogatepass')
    val, pos = _parse_value(b, 0)
    if b[pos:].strip():
        _warn("trailing_data", at_byte=pos, bytes_remaining=int(len(b) - pos))
    return val

# ================== Cleanup & JSON extraction ==================

_STRING_TOKEN = re.compile(r's:(\d+):"((?:\\.|[^"\\])*)";', re.S)

def safe_cleanup_shell_only(s: str) -> str:
    saved = []
    def _stash(m: re.Match) -> str:
        saved.append(m.group(0))
        return f'@@S{len(saved)-1}@@'
    shell = _STRING_TOKEN.sub(_stash, s)
    shell = html.unescape(shell)
    shell = re.sub(r'[ \t\f\v]+', ' ', shell)
    shell = re.sub(r'\s*;\s*', ';', shell)
    shell = re.sub(r'\s*:\s*', ':', shell)
    shell = re.sub(r'\s*\{\s*', '{', shell)
    shell = re.sub(r'\s*\}\s*', '}', shell)
    for idx, tok in enumerate(saved):
        shell = shell.replace(f'@@S{idx}@@', tok)
    return shell

LEAD_NOISE = re.compile(r'(?s)\A(?:\ufeff|[\x00-\x1F\x7F]+|[^\{\[]+)*(?=(\{|\[))')

def strip_leading_noise(s: str) -> str:
    m = LEAD_NOISE.match(s)
    return s[m.end():] if m else s

def tidy_text_and_find_json(s: str) -> str | None:
    s = s.strip().replace("\r\n", "\n").replace("\r", "\n")
    s = html.unescape(s)
    s = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', s)
    s = strip_leading_noise(s)

    def _try_blocks(open_ch: str, close_ch: str):
        starts = [m.start() for m in re.finditer(re.escape(open_ch), s)]
        for start in starts:
            depth = 0
            for i in range(start, len(s)):
                c = s[i]
                if c == open_ch:
                    depth += 1
                elif c == close_ch:
                    depth -= 1
                    if depth == 0:
                        candidate = s[start:i+1]
                        try:
                            obj = json.loads(candidate)
                            return json.dumps(obj, ensure_ascii=False)
                        except Exception:
                            repaired = _loose_json_fixes(candidate)
                            if repaired is not None:
                                return repaired
                        break
        return None

    j = _try_blocks('{', '}')
    if j is not None:
        return j
    j = _try_blocks('[', ']')
    if j is not None:
        return j
    return None

def _loose_json_fixes(txt: str) -> str | None:
    t = txt
    t = re.sub(r"(?<!\\)'([A-Za-z0-9_\-]+)'\s*:", r'"\1":', t)
    t = re.sub(r':\s*\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', lambda m: ': "' + m.group(1).replace('"', '\\"') + '"', t)
    t = re.sub(r',\s*([}\]])', r'\1', t)
    try:
        return json.dumps(json.loads(t), ensure_ascii=False)
    except Exception:
        return None

# ============================= UI =============================

APP_TITLE = "PHP Serialized → JSON"
DEFAULT_SAMPLE = (
    'a:2:{s:10:"created_at";s:19:"2025-09-15 17:28:59";'
    's:5:"items";a:1:{i:0;a:3:{s:3:"sku";s:6:"807224";s:4:"name";s:11:"Sample Name";s:11:"qty_ordered";s:6:"2.0000";}}}'
)
PROFILES_FILE = "profiles.json"

PALETTE = {
    "bg": "#0f172a", "panel": "#111827", "text": "#e5e7eb", "muted": "#cbd5e1",
    "accent": "#0ea5e9", "text_bg": "#0b1020", "text_sel": "#1e293b",
    "success": "#2ecc71", "error": "#e74c3c", "warn": "#ffcc00", "info": "#38bdf8",
}
LIGHT = {
    "bg": "#f8fafc", "panel": "#ffffff", "text": "#0f172a", "muted": "#334155",
    "accent": "#0ea5e9", "text_bg": "#ffffff", "text_sel": "#e2e8f0",
    "success": "#1e7e34", "error": "#b00020", "warn": "#9c6f00", "info": "#0369a1",
}

try:
    TtkSpinbox = ttk.Spinbox
    HAS_TTK_SPINBOX = True
except Exception:
    TtkSpinbox = None
    HAS_TTK_SPINBOX = False


class PhpToJsonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x720")
        self.minsize(900, 560)

        # state
        self.wrap_input_var = tk.BooleanVar(value=True)
        self.wrap_output_var = tk.BooleanVar(value=True)
        self.pretty_var = tk.BooleanVar(value=True)
        self.indent_var = tk.IntVar(value=2)
        self.cleanup_var = tk.BooleanVar(value=True)
        self.lenient_var = tk.BooleanVar(value=True)
        self.dark_theme = tk.BooleanVar(value=True)

        # profiles
        self.profile_var = tk.StringVar(value="")
        self._profiles = self._load_profiles()

        # theme
        self.style = ttk.Style(self)
        self.colors = {}
        self._apply_theme(dark=True)

        # menu + ui + shortcuts
        self._build_menubar()
        self._build_ui()
        self._bind_shortcuts()

        self.input_text.insert("1.0", DEFAULT_SAMPLE)
        self.set_status_ok("Ready")

    # ---------- Theme ----------
    def _apply_theme(self, *, dark: bool):
        scheme = PALETTE if dark else LIGHT
        self.colors.update(scheme)
        self.configure(bg=scheme["bg"])
        st = self.style
        st.theme_use("clam")
        st.configure(".", background=scheme["bg"], foreground=scheme["text"])
        st.configure("TFrame", background=scheme["bg"])
        st.configure("Panel.TFrame", background=scheme["panel"])
        st.configure("TLabel", background=scheme["panel"], foreground=scheme["text"])
        st.configure("Title.TLabel", background=scheme["panel"], foreground=scheme["text"], font=("Segoe UI", 12, "bold"))
        st.configure("Sublabel.TLabel", background=scheme["panel"], foreground=scheme["muted"], font=("Segoe UI", 9))
        st.configure("TButton", padding=4)  # tighter buttons
        st.map("TButton", background=[("active", scheme["accent"])])
        st.configure("Accent.TButton", padding=6)
        st.configure("TCheckbutton", background=scheme["panel"], foreground=scheme["text"])
        st.configure("TLabelframe", background=scheme["panel"], foreground=scheme["text"])
        st.configure("TLabelframe.Label", background=scheme["panel"], foreground=scheme["text"])
        st.configure("TCombobox", fieldbackground=scheme["panel"], foreground=scheme["text"])
        if HAS_TTK_SPINBOX:
            st.configure("TSpinbox", background=scheme["panel"], foreground=scheme["text"], fieldbackground=scheme["panel"])

    def _refresh_text_areas(self):
        for w in (self.input_text, self.output_text, self.diag_text):
            w.configure(bg=self.colors["text_bg"], fg=self.colors["text"],
                        insertbackground=self.colors["text"],
                        selectbackground=self.colors["text_sel"])

    # ---------- Menu ----------
    def _build_menubar(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open…", command=self.on_open, accelerator="Ctrl+O")
        file_menu.add_command(label="Save JSON…", command=self.on_save, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        settings_menu = tk.Menu(menubar, tearoff=False)
        settings_menu.add_command(label="Profiles…", command=self._show_profiles_dialog)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_menu)

    # ---------- Layout ----------
    def _build_ui(self):
        root = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        root.pack(fill=tk.BOTH, expand=True)

        # Left rail (slimmer; vertical stack)
        left = ttk.Frame(root, style="Panel.TFrame", width=200)
        right = ttk.Frame(root)
        root.add(left, weight=0)
        root.add(right, weight=1)

        ttk.Label(left, text="PHP → JSON", style="Title.TLabel").pack(anchor="w", padx=10, pady=(12, 2))
        ttk.Label(left, text="Clean & Convert", style="Sublabel.TLabel").pack(anchor="w", padx=10, pady=(0, 8))

        # Actions (short labels, narrow)
        actions = ttk.LabelFrame(left, text="Actions")
        actions.pack(fill=tk.X, padx=10, pady=(6, 10))
        for text, cmd in (
            ("Convert (F5)", self.on_convert),
            ("Open…", self.on_open),
            ("Save…", self.on_save),
            ("Copy", self.on_copy_output),
            ("Clear", self.on_clear),
        ):
            ttk.Button(actions, text=text, command=cmd).pack(fill=tk.X, padx=6, pady=3)

        # Options (checkboxes stacked vertically)
        opts = ttk.LabelFrame(left, text="Options")
        opts.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Checkbutton(opts, text="Pretty print", variable=self.pretty_var).pack(anchor="w", padx=6, pady=2)
        row = ttk.Frame(opts, style="Panel.TFrame"); row.pack(fill=tk.X, padx=6, pady=2)
        ttk.Label(row, text="Indent:").pack(side=tk.LEFT)
        spin = (TtkSpinbox if HAS_TTK_SPINBOX else tk.Spinbox)(row, from_=0, to=8, width=4, textvariable=self.indent_var)
        spin.pack(side=tk.LEFT, padx=(6,0))
        ttk.Checkbutton(opts, text="Wrap input",  variable=self.wrap_input_var,  command=self._apply_wrap).pack(anchor="w", padx=6, pady=2)
        ttk.Checkbutton(opts, text="Wrap output", variable=self.wrap_output_var, command=self._apply_wrap).pack(anchor="w", padx=6, pady=2)
        ttk.Checkbutton(opts, text="Lenient repairs (s:<len>)", variable=self.lenient_var).pack(anchor="w", padx=6, pady=2)
        ttk.Checkbutton(opts, text="Clean messy text / extract JSON", variable=self.cleanup_var).pack(anchor="w", padx=6, pady=2)

        # Bottom status + theme
        bottom_left = ttk.Frame(left, style="Panel.TFrame")
        bottom_left.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)
        ttk.Checkbutton(bottom_left, text="Dark theme", variable=self.dark_theme, command=self._toggle_theme).pack(anchor="w")

        # Right: Notebook tabs
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Input tab
        input_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(input_tab, text="Input")
        ttk.Label(input_tab, text="PHP serialized input").pack(anchor="w")
        self.input_text = tk.Text(input_tab, undo=True, wrap="word", height=12)
        self._attach_context_menu(self.input_text, quick_convert=True)  # right-click Quick Paste & Convert
        in_scroll = ttk.Scrollbar(input_tab, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=in_scroll.set)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        in_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Output tab
        output_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(output_tab, text="Output")
        ttk.Label(output_tab, text="JSON output").pack(anchor="w")
        self.output_text = tk.Text(output_tab, wrap="word", height=12)
        self._attach_context_menu(self.output_text, quick_convert=False)
        out_scroll = ttk.Scrollbar(output_tab, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=out_scroll.set)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        out_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Diagnostics tab
        diag_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(diag_tab, text="Diagnostics")
        ttk.Label(diag_tab, text="Diagnostics (repairs, notes)").pack(anchor="w")
        self.diag_text = tk.Text(diag_tab, wrap="word", height=8, state="disabled")
        self._attach_context_menu(self.diag_text, quick_convert=False, readonly=True)
        diag_scroll = ttk.Scrollbar(diag_tab, command=self.diag_text.yview)
        self.diag_text.configure(yscrollcommand=diag_scroll.set)
        self.diag_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        diag_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.diag_tab_index = self.nb.index("end") - 1  # last added

        # Status bar (bottom of window)
        bottom = ttk.Frame(self, style="Panel.TFrame")
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.status = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(bottom, textvariable=self.status, anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=4)

        # cosmetics
        self._refresh_text_areas()
        self._apply_wrap()
        self.input_text.tag_configure("error_here", background="#7f1d1d", foreground="#ffffff")

    # ---------- Context menu (Right-click Quick Paste) ----------
    def _attach_context_menu(self, text_widget: tk.Text, *, quick_convert: bool, readonly: bool=False):
        menu = tk.Menu(text_widget, tearoff=False)
        def do_paste():
            try:
                clip = self.clipboard_get()
            except Exception:
                clip = ""
            if readonly:
                return
            if text_widget.tag_ranges("sel"):
                text_widget.delete("sel.first", "sel.last")
            text_widget.insert("insert", clip)
        def do_paste_convert():
            do_paste()
            if text_widget is self.input_text:
                self.on_convert()
        def do_cut():
            if readonly: return
            try:
                sel = text_widget.get("sel.first", "sel.last")
                self.clipboard_clear(); self.clipboard_append(sel)
                text_widget.delete("sel.first", "sel.last")
            except Exception:
                pass
        def do_copy():
            try:
                sel = text_widget.get("sel.first", "sel.last")
                self.clipboard_clear(); self.clipboard_append(sel)
            except Exception:
                pass
        def do_select_all():
            text_widget.tag_add("sel", "1.0", "end-1c")
            text_widget.see("insert")
        def do_clear():
            if readonly: return
            text_widget.delete("1.0", "end")

        # order: quick actions first
        if not readonly:
            menu.add_command(label="Quick Paste", command=do_paste)
            if quick_convert:
                menu.add_command(label="Quick Paste & Convert", command=do_paste_convert)
            menu.add_separator()
            menu.add_command(label="Cut", command=do_cut)
        menu.add_command(label="Copy", command=do_copy)
        menu.add_command(label="Select All", command=do_select_all)
        if not readonly:
            menu.add_separator()
            menu.add_command(label="Clear", command=do_clear)

        def popup(event):
            # focus before showing menu so paste goes to correct widget
            text_widget.focus_set()
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        # Cross-platform bindings
        text_widget.bind("<Button-3>", popup)             # Windows/Linux
        text_widget.bind("<Button-2>", popup)             # Some macOS configs
        text_widget.bind("<Control-Button-1>", popup)     # macOS trackpad (Ctrl+Click)

    # ---------- Key bindings ----------
    def _bind_shortcuts(self):
        self.bind("<Control-Key-1>", lambda e: self.on_convert())
        self.bind("<F5>",           lambda e: self.on_convert())
        self.bind("<Control-o>",    lambda e: self.on_open())
        self.bind("<Control-s>",    lambda e: self.on_save())
        self.bind("<Control-l>",    lambda e: self.on_clear())
        self.bind("<Control-q>",    lambda e: self.destroy())
        self.bind("<Control-p>",    lambda e: self._show_profiles_dialog())

    # ---------- Helpers ----------
    def _apply_wrap(self):
        self.input_text.configure(wrap=("word" if self.wrap_input_var.get() else "none"))
        self.output_text.configure(wrap=("word" if self.wrap_output_var.get() else "none"))

    def _toggle_theme(self):
        self._apply_theme(dark=self.dark_theme.get())
        self._refresh_text_areas()

    def _clear_diag(self):
        self.diag_text.configure(state="normal")
        self.diag_text.delete("1.0", tk.END)
        self.diag_text.configure(state="disabled")
        # reset badge
        try:
            self.nb.tab(self.diag_tab_index, text="Diagnostics")
        except Exception:
            pass

    def _emit_diag(self, notes):
        if not notes:
            return
        self.diag_text.configure(state="normal")
        if self.diag_text.index("end-1c") == "1.0":
            self.diag_text.insert("1.0", "Diagnostics:\n")
        for n in notes:
            self.diag_text.insert(tk.END, f"- {n['kind']}: {json.dumps({k:v for k,v in n.items() if k!='kind'}, ensure_ascii=False)}\n")
        self.diag_text.configure(state="disabled")
        self.diag_text.see(tk.END)

        # user feedback: badge count + status ping
        try:
            current = self.nb.tab(self.diag_tab_index, "text")
        except Exception:
            current = "Diagnostics"
        count = int(re.search(r'\((\d+)\)', current).group(1)) + len(notes) if re.search(r'\((\d+)\)', current) else len(notes)
        self.nb.tab(self.diag_tab_index, text=f"Diagnostics ({count})")
        self.set_status_info(f"Diagnostics updated: {count} note(s).")

    def set_status(self, msg: str, color: str):
        self.status.set(msg)
        self.status_label.configure(foreground=color)

    def set_status_ok(self, msg: str):
        self.set_status(msg, self.colors["success"])

    def set_status_error(self, msg: str):
        self.set_status(msg, self.colors["error"])

    def set_status_warn(self, msg: str):
        self.set_status(msg, self.colors["warn"])

    def set_status_info(self, msg: str):
        self.set_status(msg, self.colors["info"])

    def clear_error_highlight(self):
        self.input_text.tag_remove("error_here", "1.0", tk.END)

    def _highlight_error_at_byte(self, byte_pos: int, raw_text: str):
        try:
            b = raw_text.encode("utf-8", errors="surrogatepass")
            prefix = b[:max(0, byte_pos)]
            prefix_txt = prefix.decode("utf-8", errors="ignore")
            ch_index = len(prefix_txt)
            start_idx = f"1.0+{ch_index}c"
            end_idx = f"1.0+{ch_index+1}c"
            self.input_text.tag_add("error_here", start_idx, end_idx)
            self.input_text.see(start_idx)
        except Exception:
            pass

    def _context_around_byte(self, raw_text: str, byte_pos: int, radius: int = 24) -> str:
        b = raw_text.encode("utf-8", errors="surrogatepass")
        start = max(0, byte_pos - radius)
        end = min(len(b), byte_pos + radius)
        snippet = b[start:end].decode("utf-8", errors="replace")
        pointer = " " * (len(b[start:byte_pos].decode("utf-8", errors="ignore"))) + "▲"
        return f"...{snippet}...\n{pointer}"

    # ---------- Profiles (menu dialog) ----------
    def _load_profiles(self) -> dict:
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _persist_profiles(self):
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._profiles, f, indent=2)
        except Exception as e:
            messagebox.showerror("Save profiles failed", str(e))

    def _collect_current_profile(self) -> dict:
        return {
            "wrap_input": self.wrap_input_var.get(),
            "wrap_output": self.wrap_output_var.get(),
            "pretty": self.pretty_var.get(),
            "indent": int(self.indent_var.get()),
            "cleanup": self.cleanup_var.get(),
            "lenient": self.lenient_var.get(),
            "dark": self.dark_theme.get(),
        }

    def _apply_profile(self, p: dict):
        self.wrap_input_var.set(bool(p.get("wrap_input", True)))
        self.wrap_output_var.set(bool(p.get("wrap_output", True)))
        self.pretty_var.set(bool(p.get("pretty", True)))
        self.indent_var.set(int(p.get("indent", 2)))
        self.cleanup_var.set(bool(p.get("cleanup", True)))
        self.lenient_var.set(bool(p.get("lenient", True)))
        self.dark_theme.set(bool(p.get("dark", True)))
        self._toggle_theme()
        self._apply_wrap()

    def _show_profiles_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Profiles")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.configure(bg=self.colors["bg"])

        frm = ttk.Frame(dlg, padding=12, style="Panel.TFrame")
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Profile name:").grid(row=0, column=0, sticky="w")
        name_var = tk.StringVar(value=self.profile_var.get())
        name_entry = ttk.Entry(frm, textvariable=name_var, width=28)
        name_entry.grid(row=0, column=1, sticky="we", padx=(8,0))

        ttk.Label(frm, text="Saved profiles:").grid(row=1, column=0, sticky="w", pady=(8,0))
        listbox = tk.Listbox(frm, height=8)
        listbox.grid(row=1, column=1, sticky="nsew", padx=(8,0), pady=(8,0))
        for k in sorted(self._profiles.keys()):
            listbox.insert(tk.END, k)

        btns = ttk.Frame(frm, style="Panel.TFrame")
        btns.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12,0))
        ttk.Button(btns, text="Save", command=lambda: self._dlg_save_profile(name_var, listbox)).pack(side=tk.LEFT)
        ttk.Button(btns, text="Load", command=lambda: self._dlg_load_profile(name_var, listbox)).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Delete", command=lambda: self._dlg_delete_profile(name_var, listbox)).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Close", command=dlg.destroy).pack(side=tk.LEFT, padx=(12,0))

        frm.grid_columnconfigure(1, weight=1)
        name_entry.focus_set()
        dlg.wait_window()

    def _dlg_save_profile(self, name_var, listbox):
        name = name_var.get().strip()
        if not name:
            self.set_status_warn("Enter a profile name.")
            return
        self._profiles[name] = self._collect_current_profile()
        self._persist_profiles()
        self.profile_var.set(name)
        self.set_status_ok(f"Profile '{name}' saved.")
        self._refresh_profiles_listbox(listbox)

    def _dlg_load_profile(self, name_var, listbox):
        name = self._get_selected_name(name_var, listbox)
        if not name:
            self.set_status_warn("Select a profile.")
            return
        self._apply_profile(self._profiles[name])
        self.profile_var.set(name)
        self.set_status_ok(f"Profile '{name}' loaded.")

    def _dlg_delete_profile(self, name_var, listbox):
        name = self._get_selected_name(name_var, listbox)
        if not name or name not in self._profiles:
            self.set_status_warn("Select a saved profile to delete.")
            return
        if messagebox.askyesno("Delete Profile", f"Delete profile '{name}'?"):
            del self._profiles[name]
            self._persist_profiles()
            self.set_status_ok(f"Profile '{name}' deleted.")
            self._refresh_profiles_listbox(listbox)

    def _get_selected_name(self, name_var, listbox) -> str | None:
        sel = listbox.curselection()
        if sel:
            return listbox.get(sel[0])
        return name_var.get().strip() or None

    def _refresh_profiles_listbox(self, listbox):
        listbox.delete(0, tk.END)
        for k in sorted(self._profiles.keys()):
            listbox.insert(tk.END, k)

    # ---------- Actions ----------
    def on_convert(self):
        global LENIENT_STRING_TERMINATOR
        self.clear_error_highlight()
        self._clear_diag()

        raw = self.input_text.get("1.0", tk.END).strip()
        if not raw:
            self.set_status_warn("Input is empty.")
            return

        try:
            if self.cleanup_var.get():
                raw = safe_cleanup_shell_only(raw)
                j = tidy_text_and_find_json(raw)
                if j is not None:
                    indent = self.indent_var.get() if self.pretty_var.get() else 0
                    out = json.dumps(json.loads(j), indent=indent, ensure_ascii=False)
                    self._print_output(out)
                    self.set_status_ok("Found embedded JSON and formatted it.")
                    return

            LENIENT_STRING_TERMINATOR = bool(self.lenient_var.get())
            indent = self.indent_var.get() if self.pretty_var.get() else 0

            try:
                obj = php_unserialize(raw)
                out = json.dumps(obj, indent=indent, ensure_ascii=False)
                self._print_output(out)
                self._emit_diag(WARNINGS)
                self.set_status_ok("Converted successfully." if not WARNINGS else f"Converted with {len(WARNINGS)} note(s).")
                return
            except ParseError:
                # Try plain JSON with leading-noise strip
                try:
                    obj = json.loads(strip_leading_noise(raw))
                    out = json.dumps(obj, indent=indent or 2, ensure_ascii=False)
                    self._print_output(out)
                    self.set_status_ok("Input was JSON. Pretty-printed.")
                    return
                except Exception:
                    raise

        except ParseError as pe:
            context = self._context_around_byte(raw, pe.pos)
            diag = {"error": str(pe), "byte_pos": pe.pos, "context": context}
            self._print_output(json.dumps(diag, indent=2, ensure_ascii=False))
            self._highlight_error_at_byte(pe.pos, raw)
            self.set_status_error(f"Parse error at byte {pe.pos}")
        except Exception as e:
            self._print_output(json.dumps({"error": str(e)}, indent=2, ensure_ascii=False))
            self.set_status_error(f"Error: {e}")

    def _print_output(self, text: str):
        self.highlight_json(self.output_text, text)
        # switch to Output tab for immediate feedback
        try:
            self.nb.select(1)  # Output tab index
        except Exception:
            pass

    def on_open(self):
        path = filedialog.askopenfilename(
            title="Open text",
            filetypes=[("Text files", "*.txt *.log *.php *.data *.ser *.dump *.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", content)
            self.set_status_info(f"Loaded: {path}")
            self.nb.select(0)  # Input tab
        except Exception as e:
            messagebox.showerror("Open failed", str(e))
            self.set_status_error(f"Open failed: {e}")

    def on_save(self):
        data = self.output_text.get("1.0", tk.END).strip()
        if not data:
            if messagebox.askyesno("No output", "Output is empty. Convert now?"):
                self.on_convert()
                data = self.output_text.get("1.0", tk.END).strip()
                if not data:
                    return
            else:
                return
        path = filedialog.asksaveasfilename(
            title="Save JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            self.set_status_ok(f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            self.set_status_error(f"Save failed: {e}")

    def on_copy_output(self):
        data = self.output_text.get("1.0", tk.END).strip()
        if not data:
            self.set_status_warn("Nothing to copy.")
            return
        self.clipboard_clear()
        self.clipboard_append(data)
        self.set_status_ok("Output copied to clipboard.")

    def on_clear(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self._clear_diag()
        self.clear_error_highlight()
        self.set_status_info("Cleared.")
        self.nb.select(0)

    # ---------- Syntax highlight ----------
    def highlight_json(self, text_widget, json_str):
        for tag in text_widget.tag_names():
            text_widget.tag_delete(tag)

        text_widget.tag_configure("key", foreground="#7dd3fc")
        text_widget.tag_configure("string", foreground="#f472b6")
        text_widget.tag_configure("number", foreground="#facc15")
        text_widget.tag_configure("boolean", foreground="#34d399")
        text_widget.tag_configure("null", foreground="#a3a3a3")

        key_pattern = r'(".*?")\s*:'
        string_pattern = r':\s*(".*?")'
        number_pattern = r'(:\s*)(-?\d+(\.\d+)?([eE][+-]?\d+)?)'
        boolean_pattern = r'(:\s*)(true|false)'
        null_pattern = r'(:\s*)null'

        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", json_str)

        for match in re.finditer(key_pattern, json_str):
            start, end = match.span(1)
            text_widget.tag_add("key", f"1.0+{start}c", f"1.0+{end}c")
        for match in re.finditer(string_pattern, json_str):
            start, end = match.span(1)
            text_widget.tag_add("string", f"1.0+{start}c", f"1.0+{end}c")
        for match in re.finditer(number_pattern, json_str):
            start, end = match.span(2)
            text_widget.tag_add("number", f"1.0+{start}c", f"1.0+{end}c")
        for match in re.finditer(boolean_pattern, json_str):
            start, end = match.span(2)
            text_widget.tag_add("boolean", f"1.0+{start}c", f"1.0+{end}c")
        for match in re.finditer(null_pattern, json_str):
            start, end = match.span(0)
            text_widget.tag_add("null", f"1.0+{start}c", f"1.0+{end}c")

    def _about(self):
        messagebox.showinfo("About", "PHP Serialized → JSON\nClean & Convert\n© 2025")

# ------------------ Entry ------------------

def main():
    app = PhpToJsonApp()
    app.mainloop()

if __name__ == "__main__":
    main()
