import os
import subprocess
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import pandas as pd
import ast
import threading
import queue
import shutil
import statistics
ANALYSIS_COMPLETE_SENTINEL = "ANALYSIS_COMPLETE"
ANALYSIS_CANCELLED_SENTINEL = "ANALYSIS_CANCELLED"
DEFAULT_EXCLUDED_DIRS = ".venv,.env,venv,env,__pycache__,.git,.vscode,build,dist"
def analyze_file(filepath, config):
    """
    Analyzes a single Python file based on the provided configuration.
    """
    result = {
        "Filename": os.path.basename(filepath),
        "Complexity": "N/A",
        "Maintainability": "N/A",
        "LLOC": "N/A",
        "Dependencies": "N/A",
        "Flake8 Errors": "N/A",
        "Pyflakes Errors": "N/A",
        "Imports Sorted": "N/A",
        "Notes": ""
    }
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        if config["run_radon"].get():
            try:
                blocks = ast.parse(code)
                visitor = __import__("radon.visitors").visitors.ComplexityVisitor.from_ast(blocks)
                result["Complexity"] = sum(c.complexity for c in visitor.blocks) if visitor.blocks else 0
                radon_raw = __import__("radon.raw").raw.analyze(code)
                radon_mi = __import__("radon.metrics").metrics.mi_visit(code, multi=True)
                result["LLOC"] = radon_raw.lloc
                result["Maintainability"] = f"{radon_mi:.2f}"
                tree = ast.parse(code)
                imports = {node.names[0].name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
                from_imports = {node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
                result["Dependencies"] = len(imports.union(from_imports))
            except Exception as e:
                result["Notes"] = f"Radon/AST parsing failed: {e}"
        if config["run_flake8"].get():
            flake8_output = subprocess.run(
                ["flake8", "--count", filepath], capture_output=True, text=True, check=False
            )
            count_str = flake8_output.stdout.strip().splitlines()
            result["Flake8 Errors"] = int(count_str[-1]) if count_str else 0
        if config["run_pyflakes"].get():
            pyflakes_output = subprocess.run(
                ["pyflakes", filepath], capture_output=True, text=True, check=False
            )
            result["Pyflakes Errors"] = len(pyflakes_output.stdout.strip().splitlines())
        if config["run_isort"].get():
            isort_output = subprocess.run(
                ["isort", "--check-only", filepath], capture_output=True, text=True, check=False
            )
            result["Imports Sorted"] = "Yes" if isort_output.returncode == 0 else "No"
    except FileNotFoundError as e:
        result["Notes"] = f"Command not found: {e.filename}. Is it in PATH?"
    except UnicodeDecodeError:
        result["Notes"] = "File is not UTF-8 encoded."
    except Exception as e:
        result["Notes"] = f"An unexpected error occurred: {e}"
    return result
class CodeAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Code Quality Analyzer")
        self.root.geometry("1400x768")
        if not self.check_dependencies():
            self.root.destroy()
            return
        self.data = []
        self.analysis_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.setup_config_vars()
        self.setup_ui()
        self.reset_live_totals()
    def check_dependencies(self):
        """Checks if required command-line tools are installed."""
        dependencies = ["flake8", "pyflakes", "isort"]
        missing = [dep for dep in dependencies if not shutil.which(dep)]
        if missing:
            messagebox.showerror(
                "Dependencies Missing",
                f"The following tools are required but not found:\n\n{', '.join(missing)}\n\n"
                f"Please install them via pip: pip install {' '.join(missing)}"
            )
            return False
        return True
    def setup_config_vars(self):
        """Initializes all user-configurable variables."""
        self.config = {
            "run_radon": tk.BooleanVar(value=True),
            "run_flake8": tk.BooleanVar(value=True),
            "run_pyflakes": tk.BooleanVar(value=True),
            "run_isort": tk.BooleanVar(value=True),
            "complexity_threshold": tk.IntVar(value=10),
            "maintainability_threshold": tk.IntVar(value=20),
            "lint_threshold": tk.IntVar(value=5),
            "file_extensions": tk.StringVar(value=".py"),
            "excluded_dirs": tk.StringVar(value=DEFAULT_EXCLUDED_DIRS),
        }
    def setup_ui(self):
        """Creates the main UI layout."""
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill="both", padx=10, pady=10)
        controls_frame = ttk.Frame(paned_window, padding=10)
        paned_window.add(controls_frame, weight=1)
        self.setup_controls_panel(controls_frame)
        results_frame = ttk.Frame(paned_window, padding=0)
        paned_window.add(results_frame, weight=4)
        self.setup_results_panel(results_frame)
        status_frame = ttk.Frame(self.root, padding=(10, 5))
        status_frame.pack(fill="x", side="bottom")
        self.status_label = ttk.Label(status_frame, text="Ready. Select a folder to begin.")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.progress_bar = ttk.Progressbar(status_frame, mode="determinate")
        self.progress_bar.pack(side="right", padx=10)
    def setup_controls_panel(self, parent):
        """Builds the left-side panel with all buttons and settings."""
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=X, pady=(0, 10))
        self.start_btn = ttk.Button(action_frame, text="Select Folder & Start", command=self.start_analysis, bootstyle=SUCCESS)
        self.start_btn.pack(side=LEFT, expand=True, fill=X, padx=(0, 5))
        self.stop_btn = ttk.Button(action_frame, text="Stop", command=self.stop_analysis, bootstyle=DANGER, state=DISABLED)
        self.stop_btn.pack(side=LEFT, expand=True, fill=X)
        self.export_btn = ttk.Button(parent, text="Export to CSV", command=self.export_csv, state=DISABLED)
        self.export_btn.pack(fill=X, pady=(5,5))
        self.summary_btn = ttk.Button(parent, text="Show Summary Report", command=self.show_summary_report, state=DISABLED)
        self.summary_btn.pack(fill=X, pady=(0,15))
        totals_frame = ttk.LabelFrame(parent, text="Live Totals", padding=10)
        totals_frame.pack(fill=X, pady=10)
        self.total_lloc_label = ttk.Label(totals_frame, text="Total LLOC: 0")
        self.total_lloc_label.pack(anchor=W)
        self.total_complexity_label = ttk.Label(totals_frame, text="Total Complexity: 0")
        self.total_complexity_label.pack(anchor=W)
        self.total_flake8_label = ttk.Label(totals_frame, text="Total Flake8 Errors: 0")
        self.total_flake8_label.pack(anchor=W)
        settings_frame = ttk.LabelFrame(parent, text="Configuration", padding=10)
        settings_frame.pack(fill=BOTH, expand=True)
        ttk.Label(settings_frame, text="High Complexity >=").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Spinbox(settings_frame, from_=1, to=100, textvariable=self.config["complexity_threshold"], width=8).grid(row=0, column=1, sticky="ew")
        ttk.Label(settings_frame, text="Low Maintainability <").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Spinbox(settings_frame, from_=1, to=100, textvariable=self.config["maintainability_threshold"], width=8).grid(row=1, column=1, sticky="ew")
        ttk.Label(settings_frame, text="Lint Errors >=").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Spinbox(settings_frame, from_=1, to=100, textvariable=self.config["lint_threshold"], width=8).grid(row=2, column=1, sticky="ew")
        ttk.Label(settings_frame, text="File Extensions").grid(row=3, column=0, sticky="w", pady=(8,2))
        ttk.Entry(settings_frame, textvariable=self.config["file_extensions"]).grid(row=3, column=1, sticky="ew")
        ttk.Label(settings_frame, text="Excluded Dirs (csv)").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(settings_frame, textvariable=self.config["excluded_dirs"]).grid(row=4, column=1, sticky="ew")
        ttk.Label(settings_frame, text="Enabled Tools").grid(row=5, column=0, columnspan=2, sticky="w", pady=(8,2))
        ttk.Checkbutton(settings_frame, text="Radon (Complexity, MI, LOC)", variable=self.config["run_radon"], bootstyle="round-toggle").grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(settings_frame, text="Flake8", variable=self.config["run_flake8"], bootstyle="round-toggle").grid(row=7, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(settings_frame, text="Pyflakes", variable=self.config["run_pyflakes"], bootstyle="round-toggle").grid(row=8, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(settings_frame, text="isort", variable=self.config["run_isort"], bootstyle="round-toggle").grid(row=9, column=0, columnspan=2, sticky="w")
        settings_frame.columnconfigure(1, weight=1)
    def setup_results_panel(self, parent):
        """Builds the right-side panel with the results Treeview."""
        columns = ("Filename", "Complexity", "Maintainability", "LLOC", "Dependencies", "Flake8 Errors", "Imports Sorted", "Notes")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", bootstyle=PRIMARY)
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
            self.tree.column(col, width=110, stretch=True, anchor=CENTER)
        self.tree.column("Filename", width=200, stretch=False, anchor=W)
        self.tree.column("Notes", width=180, stretch=False, anchor=W)
        style = ttk.Style.get_instance()
        style.configure('danger.TTreeview', background=style.colors.get('danger'), foreground='white')
        style.configure('warning.TTreeview', background=style.colors.get('warning'))
        style.configure('secondary.TTreeview', background=style.colors.get('secondary'), foreground='white')
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview, bootstyle="round-primary")
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview, bootstyle="round-primary")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side=LEFT, expand=True, fill=BOTH)
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X, before=self.tree)
    def add_result_to_tree(self, result):
        """Adds a result to the treeview and updates live totals."""
        self.data.append(result)
        tags = []
        current_file_num = len(self.data)
        total_files = self.progress_bar['maximum']
        self.status_label.config(text=f"Analyzing... ({current_file_num} of {total_files}) - {result['Filename']}")
        if isinstance(result["LLOC"], int):
            self.total_lloc += result["LLOC"]
            self.total_lloc_label.config(text=f"Total LLOC: {self.total_lloc}")
        if isinstance(result["Complexity"], int):
            self.total_complexity += result["Complexity"]
            self.total_complexity_label.config(text=f"Total Complexity: {self.total_complexity}")
        if isinstance(result["Flake8 Errors"], int):
            self.total_flake8 += result["Flake8 Errors"]
            self.total_flake8_label.config(text=f"Total Flake8 Errors: {self.total_flake8}")
        is_error = result["Notes"] or any(val in ("Error", "Parse Error") for val in result.values())
        if is_error:
            tags.append('secondary.TTreeview')
        else:
            try:
                if float(result.get("Maintainability", 100)) < self.config["maintainability_threshold"].get():
                    tags.append('danger.TTreeview')
                elif int(result.get("Complexity", 0)) >= self.config["complexity_threshold"].get():
                    tags.append('warning.TTreeview')
            except (ValueError, TypeError):
                pass
        self.tree.insert("", "end", values=list(result.values()), tags=tags)
    def finalize_analysis(self, status):
        """Updates the UI after analysis is complete or stopped."""
        total_files = len(self.data)
        if status == ANALYSIS_COMPLETE_SENTINEL:
            msg = f"✅ Analysis complete. Processed {total_files} files."
            self.progress_bar["value"] = self.progress_bar["maximum"]
            if self.data:
                self.summary_btn.config(state=NORMAL)
        else: # Cancelled
            msg = f"🛑 Analysis stopped by user. Processed {total_files} files."
        self.status_label.config(text=msg)
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        if self.data:
            self.export_btn.config(state=NORMAL)
    def reset_ui_for_analysis(self):
        """Resets the UI state before a new analysis begins."""
        self.data.clear()
        self.stop_event.clear()
        self.tree.delete(*self.tree.get_children())
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.export_btn.config(state=DISABLED)
        self.summary_btn.config(state=DISABLED)
        self.progress_bar["value"] = 0
        self.status_label.config(text="Scanning for files...")
        self.reset_live_totals()
    def reset_live_totals(self):
        self.total_lloc = 0
        self.total_complexity = 0
        self.total_flake8 = 0
        self.total_lloc_label.config(text="Total LLOC: 0")
        self.total_complexity_label.config(text="Total Complexity: 0")
        self.total_flake8_label.config(text="Total Flake8 Errors: 0")
    def show_summary_report(self):
        """Creates a Toplevel window with a summary and guide."""
        if not self.data: return
        numeric_data = [d for d in self.data if not (d['Notes'] or 'N/A' in d.values())]
        if not numeric_data:
            messagebox.showinfo("Summary Unavailable", "No valid data to generate a summary.")
            return
        avg_mi = statistics.mean([float(d['Maintainability']) for d in numeric_data])
        avg_cc = statistics.mean([d['Complexity'] for d in numeric_data])
        avg_lloc = statistics.mean([d['LLOC'] for d in numeric_data])
        top_5_complex = sorted(numeric_data, key=lambda d: d['Complexity'], reverse=True)[:5]
        top_5_unmaintainable = sorted(numeric_data, key=lambda d: float(d['Maintainability']))[:5]
        win = ttk.Toplevel(self.root, title="Analysis Summary Report")
        win.geometry("800x600")
        main_frame = ttk.Frame(win, padding=15)
        main_frame.pack(fill=BOTH, expand=TRUE)
        avg_frame = ttk.LabelFrame(main_frame, text="Project Averages", padding=10)
        avg_frame.pack(fill=X, pady=5)
        avg_frame.columnconfigure((0,1,2), weight=1)
        ttk.Label(avg_frame, text=f"Maintainability: {avg_mi:.2f}", font="-weight bold").grid(row=0, column=0)
        ttk.Label(avg_frame, text=f"Complexity: {avg_cc:.2f}", font="-weight bold").grid(row=0, column=1)
        ttk.Label(avg_frame, text=f"LLOC per File: {avg_lloc:.2f}", font="-weight bold").grid(row=0, column=2)
        watch_frame = ttk.LabelFrame(main_frame, text="Files to Watch", padding=10)
        watch_frame.pack(fill=X, pady=10)
        watch_frame.columnconfigure((0,1), weight=1)
        ttk.Label(watch_frame, text="Highest Complexity", font="-underline 1").grid(row=0, column=0, pady=(0,5))
        for i, item in enumerate(top_5_complex):
            ttk.Label(watch_frame, text=f"{item['Filename']} ({item['Complexity']})").grid(row=i+1, column=0, sticky=W)
        ttk.Label(watch_frame, text="Lowest Maintainability", font="-underline 1").grid(row=0, column=1, pady=(0,5))
        for i, item in enumerate(top_5_unmaintainable):
            ttk.Label(watch_frame, text=f"{item['Filename']} ({item['Maintainability']})").grid(row=i+1, column=1, sticky=W)
        guide_frame = ttk.LabelFrame(main_frame, text="💡 Metrics Guide", padding=10)
        guide_frame.pack(fill=BOTH, expand=TRUE, pady=5)
        guide_text = """
Measures how easy it is to support and change the code. Higher is better.
- **> 20 (Grade A):** Good. The code is likely well-structured and maintainable.
- **10-19 (Grade B):** Okay. Could be improved, might have some complex areas.
- **< 10 (Grade C):** Problematic. Code is difficult to maintain and needs refactoring.
Measures the number of independent paths through the code. Lower is better.
- **1-10:** Good. Simple and well-structured.
- **11-20:** Moderate. More complex, consider refactoring into smaller functions.
- **> 20:** High. Very complex, hard to test and maintain. A prime candidate for simplification.
Counts the actual executable statements, ignoring comments and blank lines. It's a better measure of code size than physical lines. Very large files (> 400-500 LLOC) are often doing too much and should be broken down.
These indicate violations of Python's style guide (PEP 8) or potential logical errors. The goal should always be **zero** errors.
Shows how many other modules a file relies on. High coupling can make a file harder to test and reuse in isolation.
"""
        st = ScrolledText(guide_frame, padding=10, hbar=False, bootstyle='round')
        st.insert(END, guide_text)
        st.config(state=DISABLED)
        st.pack(fill=BOTH, expand=TRUE)
    def start_analysis(self):
        folder = filedialog.askdirectory()
        if not folder: return
        self.reset_ui_for_analysis()
        thread = threading.Thread(target=self._run_analysis_worker, args=(folder,), daemon=True)
        thread.start()
        self.process_queue()
    def stop_analysis(self):
        self.stop_event.set()
        self.status_label.config(text="🛑 Stopping analysis...")
        self.stop_btn.config(state=DISABLED)
    def _run_analysis_worker(self, folder):
        extensions = [ext.strip() for ext in self.config["file_extensions"].get().split(',')]
        excluded_dirs = {d.strip() for d in self.config["excluded_dirs"].get().split(',') if d.strip()}
        files_to_analyze = []
        for root_dir, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    files_to_analyze.append(os.path.join(root_dir, file))
        self.analysis_queue.put(len(files_to_analyze))
        for filepath in files_to_analyze:
            if self.stop_event.is_set(): break
            self.analysis_queue.put(analyze_file(filepath, self.config))
        sentinel = ANALYSIS_CANCELLED_SENTINEL if self.stop_event.is_set() else ANALYSIS_COMPLETE_SENTINEL
        self.analysis_queue.put(sentinel)
    def process_queue(self):
        try:
            while True:
                item = self.analysis_queue.get_nowait()
                if isinstance(item, int):
                    self.progress_bar["maximum"] = item
                    self.status_label.config(text=f"Found {item} files to analyze...")
                    continue
                if item in (ANALYSIS_COMPLETE_SENTINEL, ANALYSIS_CANCELLED_SENTINEL):
                    self.finalize_analysis(item)
                    return
                self.progress_bar["value"] += 1
                self.add_result_to_tree(item)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)
    def export_csv(self):
        if not self.data: return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Save Report")
        if not path: return
        try:
            pd.DataFrame(self.data).to_csv(path, index=False)
            messagebox.showinfo("Export Successful", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred:\n{e}")
    def sort_column(self, col, reverse):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            items.sort(key=lambda t: float(t[0]), reverse=reverse)
        except (ValueError, TypeError):
            items.sort(key=lambda t: str(t[0]).lower(), reverse=reverse)
        for index, (_, k) in enumerate(items):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
if __name__ == "__main__":
    root = ttk.Window(themename="cyborg")
    app = CodeAnalyzerApp(root)
    if root.winfo_exists():
        root.mainloop()
