import os
import tkinter as tk
from tkinter import filedialog

class DirectoryTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TK-Midnight Tree")
        self.root.configure(bg="#0f0f10")
        self.root.geometry("600x800")

        self.create_top_bar()
        self.create_filter_bar()
        self.create_tree_output()
        self.render_tree()

    def create_top_bar(self):
        top = tk.Frame(self.root, bg="#0f0f10")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        top.grid_columnconfigure(0, weight=1)

        self.path_var = tk.StringVar(value=os.getcwd())
        tk.Entry(top, textvariable=self.path_var, bg="#1b1c20", fg="#8be9fd",
                 insertbackground="#8be9fd", width=40).grid(row=0, column=0, sticky="ew", padx=5)

        tk.Button(top, text="Browse", command=self.browse_folder,
                  bg="#282a36", fg="#ff79c6").grid(row=0, column=1, padx=5)

        tk.Label(top, text="Depth", bg="#0f0f10", fg="#bd93f9").grid(row=0, column=2, padx=(10, 0))
        self.depth_var = tk.IntVar(value=3)
        tk.Spinbox(top, from_=1, to=20, textvariable=self.depth_var,
                   width=3, bg="#1b1c20", fg="#8be9fd",
                   insertbackground="#8be9fd").grid(row=0, column=3, padx=5)

        tk.Button(top, text="Refresh", command=self.render_tree,
                  bg="#44475a", fg="#50fa7b").grid(row=0, column=4, padx=5)

        tk.Button(top, text="Copy", command=self.copy_to_clipboard,
                  bg="#6272a4", fg="#f8f8f2").grid(row=0, column=5, padx=5)

    def create_filter_bar(self):
        filter_bar = tk.Frame(self.root, bg="#0f0f10")
        filter_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        filter_bar.grid_columnconfigure(1, weight=1)
        filter_bar.grid_columnconfigure(3, weight=1)

        tk.Label(filter_bar, text="Exclude Folders:", bg="#0f0f10", fg="#bd93f9").grid(row=0, column=0, padx=5)
        self.exclude_var = tk.StringVar(value="__pycache__,node_modules,.venv")
        tk.Entry(filter_bar, textvariable=self.exclude_var,
                 bg="#1b1c20", fg="#8be9fd").grid(row=0, column=1, sticky="ew", padx=5)

        tk.Label(filter_bar, text="Exclude Keywords:", bg="#0f0f10", fg="#bd93f9").grid(row=0, column=2, padx=5)
        self.keyword_var = tk.StringVar(value="temp,backup")
        tk.Entry(filter_bar, textvariable=self.keyword_var,
                 bg="#1b1c20", fg="#8be9fd").grid(row=0, column=3, sticky="ew", padx=5)

    def create_tree_output(self):
        output_frame = tk.Frame(self.root, bg="#0f0f10")
        output_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        scrollbar = tk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_output = tk.Text(
            output_frame, wrap="none", bg="#1a1b1f", fg="#f8f8f2",
            insertbackground="#f8f8f2", font=("Courier", 10),
            yscrollcommand=scrollbar.set
        )
        self.text_output.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_output.yview)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            self.render_tree()

    def render_tree(self):
        path = self.path_var.get().strip()
        max_depth = self.depth_var.get()
        exclude_folders = [x.strip() for x in self.exclude_var.get().split(",") if x.strip()]
        exclude_keywords = [x.strip().lower() for x in self.keyword_var.get().split(",") if x.strip()]

        self.text_output.delete("1.0", tk.END)
        if not os.path.isdir(path):
            self.text_output.insert(tk.END, "Invalid path.")
            return

        self.text_output.insert(tk.END, f"📁 Directory tree for: {path}\n\n")
        self._print_tree(path, 0, max_depth, "", exclude_folders, exclude_keywords)

    def _print_tree(self, path, depth, max_depth, indent, exclude_folders, exclude_keywords):
        if depth >= max_depth:
            return
        try:
            items = sorted(os.listdir(path))
        except Exception as e:
            self.text_output.insert(tk.END, indent + f"[Error] {e}\n")
            return

        for index, item in enumerate(items):
            full_path = os.path.join(path, item)
            item_lower = item.lower()

            if item in exclude_folders or any(keyword in item_lower for keyword in exclude_keywords):
                continue

            prefix = "└── " if index == len(items) - 1 else "├── "
            self.text_output.insert(tk.END, indent + prefix + item + "\n")

            if os.path.isdir(full_path):
                new_indent = indent + ("    " if index == len(items) - 1 else "│   ")
                self._print_tree(full_path, depth + 1, max_depth, new_indent, exclude_folders, exclude_keywords)

    def copy_to_clipboard(self):
        tree_text = self.text_output.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(tree_text)
        self.root.update()

def launch_gui():
    root = tk.Tk()
    DirectoryTreeApp(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
