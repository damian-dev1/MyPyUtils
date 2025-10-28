import os
import time
import tkinter as tk
from tkinter import ttk, filedialog
import platform
import subprocess
MIDNIGHT_THEME = {
    "bg_main": "#0f0f10",
    "bg_entry": "#1b1c20",
    "bg_output": "#1a1b1f",
    "fg_text": "#f8f8f2",
    "fg_entry": "#8be9fd",
    "fg_label": "#bd93f9",
    "btn_browse_bg": "#282a36",
    "btn_browse_fg": "#ff79c6",
    "btn_refresh_bg": "#44475a",
    "btn_refresh_fg": "#50fa7b",
    "btn_copy_bg": "#6272a4",
    "btn_copy_fg": "#f8f8f2",
}
class FileManagerDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TKM Directory Tree")
        self.geometry("700x600")
        self.theme = MIDNIGHT_THEME
        self.configure(bg=self.theme["bg_main"])
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TNotebook", background=self.theme["bg_main"])
        self.style.configure("TNotebook.Tab",
                             background=self.theme["bg_entry"],
                             foreground=self.theme["fg_text"],
                             lightcolor=self.theme["bg_main"],
                             darkcolor=self.theme["bg_main"],
                             borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[('selected', self.theme["bg_main"])],
                       foreground=[('selected', self.theme["fg_entry"])])
        self.style.configure('TSpinbox',
                             fieldbackground=self.theme["bg_entry"],
                             background=self.theme["bg_entry"],
                             foreground=self.theme["fg_entry"],
                             arrowcolor=self.theme["fg_label"])
        self.style.map('TSpinbox',
                       fieldbackground=[('readonly', self.theme["bg_entry"])],
                       selectbackground=[('readonly', self.theme["btn_browse_bg"])],
                       foreground=[('readonly', self.theme["fg_entry"])])
        self._init_string_vars()
        self.quick_stats_options = {
            "folders": tk.BooleanVar(value=True),
            "files": tk.BooleanVar(value=True),
            "total_size": tk.BooleanVar(value=True),
            "largest_file": tk.BooleanVar(value=False),
            "deepest_folder": tk.BooleanVar(value=False),
            "scan_time": tk.BooleanVar(value=False),
            "file_types": tk.BooleanVar(value=False),
        }
        self._create_top_bar()
        self._create_bottom_bar()
        self._create_layout()
        self.render_tree()
    def _init_string_vars(self):
        self.path_var = tk.StringVar(value=os.getcwd())
        self.depth_var = tk.IntVar(value=3)
        self.exclude_folders_var = tk.StringVar(value="__pycache__,node_modules,.venv,.git")
        self.exclude_keywords_var = tk.StringVar(value="temp,backup")
        self.status_var = tk.StringVar(value="Ready")
        self.stats = {
            "folders": 0,
            "files": 0,
            "total_size": 0,
            "largest_file": ("", 0),
            "max_depth_path": ("", 0),
            "start_time": 0,
            "file_types": {}
        }
        self.plain_tree_text = ""
    def _create_top_bar(self):
        top_bar = tk.Frame(self, height=30, bg=self.theme["bg_main"])
        top_bar.pack(side='top', fill='x')
        tk.Label(top_bar, text="TKM Directory Tree 📁", font=("Segoe UI", 10, "bold"), fg=self.theme["fg_label"], bg=self.theme["bg_main"]).pack(side='left', padx=10)
    def _create_bottom_bar(self):
        bottom_bar = tk.Frame(self, height=25, bg=self.theme["bg_main"])
        bottom_bar.pack(side='bottom', fill='x')
        tk.Label(bottom_bar, textvariable=self.status_var, anchor='w', fg=self.theme["fg_text"], bg=self.theme["bg_main"]).pack(side='left', padx=10)
    def _create_layout(self):
        left_panel = tk.Frame(self, width=180, bg=self.theme["bg_main"])
        left_panel.pack(side='left', fill='y', padx=5, pady=5)
        left_panel.pack_propagate(False)
        main_content = tk.Frame(self, bg=self.theme["bg_main"])
        main_content.pack(side='right', fill='both', expand=True)
        self._create_control_panel(left_panel)
        self._create_main_view(main_content)
    def _create_control_panel(self, parent):
        tree_frame = tk.LabelFrame(parent, text="Directory Tree", bg=self.theme["bg_main"], fg=self.theme["fg_label"], relief=tk.GROOVE, bd=2)
        tree_frame.pack(fill='x', padx=5, pady=5)
        path_row = tk.Frame(tree_frame, bg=self.theme["bg_main"])
        path_row.pack(fill='x', pady=2)
        tk.Label(path_row, text="Root Path:", fg=self.theme["fg_label"], bg=self.theme["bg_main"]).pack(side='left')
        tk.Entry(path_row, textvariable=self.path_var, bg=self.theme["bg_entry"], fg=self.theme["fg_entry"], insertbackground=self.theme["fg_entry"], relief=tk.FLAT, bd=1, selectbackground=self.theme["btn_copy_bg"]).pack(side='left', fill='x', expand=True, padx=5)
        action_row = tk.Frame(tree_frame, bg=self.theme["bg_main"])
        action_row.pack(fill='x', pady=2)
        tk.Button(action_row, text="Browse", command=self.browse_folder, bg=self.theme["btn_browse_bg"], fg=self.theme["btn_browse_fg"], activebackground=self.theme["btn_browse_bg"], activeforeground=self.theme["btn_browse_fg"], relief=tk.FLAT, bd=1).pack(side='left', expand=True, padx=2)
        tk.Button(action_row, text="Copy Tree", command=self.copy_to_clipboard, bg=self.theme["btn_copy_bg"], fg=self.theme["btn_copy_fg"], activebackground=self.theme["btn_copy_bg"], activeforeground=self.theme["btn_copy_fg"], relief=tk.FLAT, bd=1).pack(side='left', expand=True, padx=2)
        filter_frame = tk.LabelFrame(tree_frame, text="Filters", bg=self.theme["bg_main"], fg=self.theme["fg_label"], relief=tk.GROOVE, bd=2)
        filter_frame.pack(fill='x', pady=5)
        tk.Label(filter_frame, text="Exclude Folders:", fg=self.theme["fg_label"], bg=self.theme["bg_main"], anchor='w').pack(anchor='w')
        tk.Entry(filter_frame, textvariable=self.exclude_folders_var, bg=self.theme["bg_entry"], fg=self.theme["fg_entry"], insertbackground=self.theme["fg_entry"], relief=tk.FLAT, bd=1, selectbackground=self.theme["btn_copy_bg"]).pack(fill='x', pady=2)
        tk.Label(filter_frame, text="Exclude Keywords:", fg=self.theme["fg_label"], bg=self.theme["bg_main"], anchor='w').pack(anchor='w')
        tk.Entry(filter_frame, textvariable=self.exclude_keywords_var, bg=self.theme["bg_entry"], fg=self.theme["fg_entry"], insertbackground=self.theme["fg_entry"], relief=tk.FLAT, bd=1, selectbackground=self.theme["btn_copy_bg"]).pack(fill='x', pady=2)
        refresh_row = tk.Frame(tree_frame, bg=self.theme["bg_main"])
        refresh_row.pack(fill='x', pady=2)
        tk.Button(refresh_row, text="Refresh", command=self.render_tree, bg=self.theme["btn_refresh_bg"], fg=self.theme["btn_refresh_fg"], activebackground=self.theme["btn_refresh_bg"], activeforeground=self.theme["btn_refresh_fg"], relief=tk.FLAT, bd=1).pack(side='left', expand=True, padx=2)
        depth_box = tk.Frame(refresh_row, bg=self.theme["bg_main"])
        depth_box.pack(side='left', padx=(10, 0))
        tk.Label(depth_box, text="Depth:", fg=self.theme["fg_label"], bg=self.theme["bg_main"]).pack(side='left')
        ttk.Spinbox(depth_box, from_=1, to=20, textvariable=self.depth_var, width=5).pack(side='left', padx=2)
        stats_frame = tk.LabelFrame(parent, text="Quick Stats", bg=self.theme["bg_main"], fg=self.theme["fg_label"], relief=tk.GROOVE, bd=2)
        stats_frame.pack(fill='x', padx=5, pady=10)
        self.quick_stats_label = tk.Label(stats_frame, justify='left', anchor='w', fg=self.theme["fg_text"], bg=self.theme["bg_main"])
        self.quick_stats_label.pack(fill='x')
        options_frame = tk.Frame(stats_frame, bg=self.theme["bg_main"])
        options_frame.pack(fill='x', pady=5)
        for key, var in self.quick_stats_options.items():
            cb = tk.Checkbutton(options_frame, text=key.replace("_", " ").title(), variable=var, anchor='w',
                                bg=self.theme["bg_main"], fg=self.theme["fg_text"],
                                activebackground=self.theme["bg_main"], activeforeground=self.theme["fg_text"],
                                selectcolor=self.theme["btn_refresh_bg"],
                                relief=tk.FLAT, bd=1)
            cb.pack(fill='x', padx=5)
    def _create_main_view(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill='both', expand=True)
        tree_tab = tk.Frame(self.notebook, bg=self.theme["bg_main"])
        self.notebook.add(tree_tab, text='Tree View')
        tree_scroll = tk.Scrollbar(tree_tab, bg=self.theme["bg_main"], troughcolor=self.theme["bg_output"], activebackground=self.theme["fg_text"], highlightbackground=self.theme["bg_main"])
        tree_scroll.pack(side='right', fill='y')
        self.tree_output_text = tk.Text(tree_tab, wrap='none', yscrollcommand=tree_scroll.set, bg=self.theme["bg_output"], fg=self.theme["fg_text"], insertbackground=self.theme["fg_text"], selectbackground=self.theme["btn_copy_bg"])
        self.tree_output_text.pack(side='left', fill='both', expand=True)
        tree_scroll.config(command=self.tree_output_text.yview)
        stats_tab = tk.Frame(self.notebook, bg=self.theme["bg_main"])
        self.notebook.add(stats_tab, text='Detailed Stats')
        self.detailed_stats_text = tk.Text(stats_tab, wrap='word', state='disabled', bg=self.theme["bg_output"], fg=self.theme["fg_text"], insertbackground=self.theme["fg_text"], selectbackground=self.theme["btn_copy_bg"])
        self.detailed_stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        self.tree_output_text.tag_configure("folder", foreground=self.theme["fg_label"], underline=False)
        self.tree_output_text.tag_configure("file", font=("Segoe UI", 10), foreground=self.theme["fg_entry"])
        self.tree_output_text.tag_configure("error", foreground="#ff5555")
        self.tree_output_text.tag_configure("line", foreground=self.theme["btn_copy_bg"])
        self.detailed_stats_text.tag_configure("bold", font=("Segoe UI", 10, "bold"))
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            self.render_tree()
    def render_tree(self):
        self.stats = {
            "folders": 0,
            "files": 0,
            "total_size": 0,
            "largest_file": ("", 0),
            "max_depth_path": ("", 0),
            "start_time": time.time(),
            "file_types": {}
        }
        path = self.path_var.get().strip()
        max_depth = self.depth_var.get()
        exclude_folders = {x.strip() for x in self.exclude_folders_var.get().split(',')}
        exclude_keywords = {x.strip().lower() for x in self.exclude_keywords_var.get().split(',')}
        self.tree_output_text.config(state='normal')
        self.tree_output_text.delete("1.0", tk.END)
        if not os.path.isdir(path):
            error_msg = "❌ Invalid path.\n"
            self.tree_output_text.insert(tk.END, error_msg, "error")
            self.plain_tree_text = "Invalid path.\n"
            self._show_status("Invalid path.")
            self.tree_output_text.config(state='disabled')
            self._update_stats_display(0)
            return
        self.plain_tree_text = f"Directory tree for: {path}\n\n"
        self.tree_output_text.insert(tk.END, f"📁 Directory tree for: {path}\n\n", "line")
        self.stats["folders"] += 1
        self.stats["max_depth_path"] = (path, 0)
        self._generate_tree_output(path, 0, max_depth, "", exclude_folders, exclude_keywords)
        self.tree_output_text.config(state='disabled')
        elapsed = time.time() - self.stats["start_time"]
        self._update_stats_display(elapsed)
        self._show_status("Tree rendered.")
    def _generate_tree_output(self, path, depth, max_depth, indent, exclude_folders, exclude_keywords):
        if depth >= max_depth:
            return
        try:
            items = sorted(os.listdir(path))
        except Exception as e:
            error_line = indent + f"❌ [Error] {e}\n"
            self.tree_output_text.insert(tk.END, error_line, "error")
            self.plain_tree_text += error_line.strip() + "\n"
            return
        for index, item in enumerate(items):
            item_lower = item.lower()
            if item in exclude_folders or any(k in item_lower for k in exclude_keywords):
                continue
            full_path = os.path.join(path, item)
            prefix = "└── " if index == len(items) - 1 else "├── "
            self.tree_output_text.insert(tk.END, indent + prefix, "line")
            self.plain_tree_text += indent + prefix + item + "\n"
            icon = "📁" if os.path.isdir(full_path) else "📄"
            if os.path.isdir(full_path):
                folder_tag = f"folder_{full_path}"
                self.tree_output_text.insert(tk.END, icon + " " + item + "\n", ("folder", folder_tag))
                self.tree_output_text.tag_bind(folder_tag, "<Button-1>", lambda e, p=full_path: self._open_item(p))
                self.tree_output_text.tag_bind(folder_tag, "<Enter>", lambda e, t=folder_tag: self._on_hover(t, True))
                self.tree_output_text.tag_bind(folder_tag, "<Leave>", lambda e, t=folder_tag: self._on_hover(t, False))
                self.stats["folders"] += 1
                if depth + 1 > self.stats["max_depth_path"][1]:
                    self.stats["max_depth_path"] = (full_path, depth + 1)
                new_indent = indent + ("    " if index == len(items) - 1 else "│   ")
                self._generate_tree_output(full_path, depth + 1, max_depth, new_indent, exclude_folders, exclude_keywords)
            else:
                file_tag = f"file_{full_path}"
                self.tree_output_text.insert(tk.END, icon + " " + item + "\n", ("file", file_tag))
                self.tree_output_text.tag_bind(file_tag, "<Button-1>", lambda e, p=full_path: self._open_item(p))
                self.tree_output_text.tag_bind(file_tag, "<Enter>", lambda e, t=file_tag: self._on_hover(t, True))
                self.tree_output_text.tag_bind(file_tag, "<Leave>", lambda e, t=file_tag: self._on_hover(t, False))
                self.stats["files"] += 1
                ext = os.path.splitext(item)[1].lower()
                self.stats["file_types"][ext] = self.stats["file_types"].get(ext, 0) + 1
                try:
                    size = os.path.getsize(full_path)
                    self.stats["total_size"] += size
                    if size > self.stats["largest_file"][1]:
                        self.stats["largest_file"] = (full_path, size)
                except:
                    pass
    def _on_hover(self, tag, entering):
        if entering:
            self.tree_output_text.config(cursor="hand2")
            self.tree_output_text.tag_configure(tag, underline=True)
        else:
            self.tree_output_text.config(cursor="")
            self.tree_output_text.tag_configure(tag, underline=False)
    def _open_item(self, path):
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", path])
            elif system == "Linux":
                subprocess.Popen(["xdg-open", path])
            else:
                self._show_status(f"Unsupported OS: {system}")
                return
            self._show_status(f"Opened: {os.path.basename(path)}")
        except Exception as e:
            self._show_status(f"Error opening: {e}")
    def copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.plain_tree_text)
        self.update()
        self._show_status("Tree copied to clipboard.")
    def _show_status(self, message):
        self.status_var.set(message)
        self.update_idletasks()
    def _update_stats_display(self, elapsed):
        largest_name, largest_size = self.stats["largest_file"]
        max_path, max_depth = self.stats["max_depth_path"]
        file_types = sorted(self.stats["file_types"].items(), key=lambda x: x[1], reverse=True)[:5]
        quick_lines = []
        if self.quick_stats_options["folders"].get():
            quick_lines.append(f"Folders: {self.stats['folders']}")
        if self.quick_stats_options["files"].get():
            quick_lines.append(f"Files: {self.stats['files']}")
        if self.quick_stats_options["total_size"].get():
            quick_lines.append(f"Total Size: {self._format_size(self.stats['total_size'])}")
        if self.quick_stats_options["largest_file"].get():
            quick_lines.append(f"Largest File: {os.path.basename(largest_name)}")
        if self.quick_stats_options["deepest_folder"].get():
            quick_lines.append(f"Deepest Folder: {max_path}")
        if self.quick_stats_options["scan_time"].get():
            quick_lines.append(f"Scan Time: {elapsed:.2f} sec")
        if self.quick_stats_options["file_types"].get():
            quick_lines.append("Top File Types:")
            quick_lines += [f"  • {ext or '[no ext]'}: {count}" for ext, count in file_types]
        self.quick_stats_label.config(text="\n".join(quick_lines))
        self.detailed_stats_text.config(state='normal')
        self.detailed_stats_text.delete("1.0", tk.END)
        self.detailed_stats_text.insert(tk.END, "📊 Detailed Stats\n\n")
        self.detailed_stats_text.insert(tk.END, f"• Largest File:\n  {os.path.basename(largest_name)} ({self._format_size(largest_size)})\n", "bold")
        self._add_clickable_path(self.detailed_stats_text, largest_name)
        self.detailed_stats_text.insert(tk.END, f"\n\n• Deepest Folder:\n  {max_path} (depth {max_depth})\n", "bold")
        self._add_clickable_path(self.detailed_stats_text, max_path)
        self.detailed_stats_text.insert(tk.END, f"\n\n• Scan Time:\n  {elapsed:.2f} seconds\n", "bold")
        self.detailed_stats_text.insert(tk.END, "\n\n• Top 5 File Types:\n", "bold")
        for ext, count in file_types:
            self.detailed_stats_text.insert(tk.END, f"  • {ext or '[no ext]'}: {count}\n")
        self.detailed_stats_text.config(state='disabled')
    def _add_clickable_path(self, widget, path):
        tag = f"path_{path}"
        widget.insert(tk.END, f"  {path}\n", tag)
        widget.tag_configure(tag, foreground=self.theme["fg_entry"], underline=True)
        widget.tag_bind(tag, "<Button-1>", lambda e, p=path: self._open_item(p))
        widget.tag_bind(tag, "<Enter>", lambda e, t=tag: self._on_hover_detailed(widget, t, True))
        widget.tag_bind(tag, "<Leave>", lambda e, t=tag: self._on_hover_detailed(widget, t, False))
    def _on_hover_detailed(self, widget, tag, entering):
        if entering:
            widget.config(cursor="hand2")
            widget.tag_configure(tag, underline=True)
        else:
            widget.config(cursor="")
            widget.tag_configure(tag, underline=False)
    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
if __name__ == "__main__":
    app = FileManagerDashboard()
    app.mainloop()
