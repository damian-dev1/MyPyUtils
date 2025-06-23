import os
import psutil
import time
import logging
import platform
import tkinter as tk
from ttkbootstrap import Style
from tkinter import ttk, messagebox, filedialog
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Platform compatibility check
def check_platform():
    system = platform.system()
    logging.info(f"Running on {system}")

check_platform()

# Secure File Deletion Function
def secure_delete(file_path, passes=3):
    """Overwrites a file with random data multiple times before deletion."""
    if os.path.exists(file_path):
        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, "wb") as f:
                for _ in range(passes):
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())

            os.remove(file_path)
            logging.info(f"File '{file_path}' securely deleted after {passes} overwrite passes.")
        except Exception as e:
            logging.error(f"Failed to securely delete '{file_path}': {e}")
    else:
        logging.error(f"File '{file_path}' does not exist.")

# Process Termination Function
def terminate_related_processes(file_path):
    """Finds and terminates processes locking the file."""
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            for f in proc.open_files():
                if f.path == file_path:
                    logging.info(f"Terminating process {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.terminate()
                    proc.wait()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        except Exception as e:
            logging.error(f"Error terminating process: {e}")

# GUI Class
class BootstrapGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File & Folder Deletion GUI")
        self.geometry("500x450")
        
        # Apply Bootstrap styling
        self.style = Style(theme="darkly")  
        
        self.selected_path = None
        self.scheduled_task = None
        self.secure_delete_enabled = tk.BooleanVar(value=True)  # Checkbox for secure deletion
        self.interval_var = tk.IntVar(value=10)  # Default deletion interval (in seconds)

        self.create_widgets()

    def create_widgets(self):
        """Create styled widgets with Bootstrap-like aesthetics."""
        
        # Title Label
        title_label = ttk.Label(self, text="Secure Deletion", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Selection Buttons
        file_button = ttk.Button(self, text="Select File", command=self.select_file)
        file_button.pack(pady=5)

        folder_button = ttk.Button(self, text="Select Folder", command=self.select_folder)
        folder_button.pack(pady=5)

        # Display Selected Path
        self.path_display = ttk.Label(self, text="No file/folder selected", font=("Arial", 12))
        self.path_display.pack(pady=5)

        # Secure Delete Checkbox
        self.secure_delete_checkbox = ttk.Checkbutton(self, text="Enable Secure Delete", variable=self.secure_delete_enabled)
        self.secure_delete_checkbox.pack(pady=5)

        # Interval Selection
        ttk.Label(self, text="Set Deletion Interval (seconds):").pack(pady=5)
        self.interval_entry = ttk.Entry(self, textvariable=self.interval_var, width=10)
        self.interval_entry.pack(pady=5)

        # Delete Button (Immediate for files)
        delete_button = ttk.Button(self, text="Delete Now", command=self.delete_now)
        delete_button.pack(pady=10)

        # Schedule Button (Only for folders)
        self.schedule_button = ttk.Button(self, text="Start Auto-Deletion", command=self.start_scheduled_deletion)
        self.schedule_button.pack(pady=5)

        # Stop Schedule Button
        stop_button = ttk.Button(self, text="Stop Auto-Deletion", command=self.stop_scheduled_deletion)
        stop_button.pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(self, orient="horizontal", length=200, mode="indeterminate")
        self.progress.pack(pady=10)

    def select_file(self):
        """Open file explorer for single file selection."""
        file = filedialog.askopenfilename(title="Select file for deletion")
        if file:
            self.selected_path = file
            self.path_display.config(text=file)

    def select_folder(self):
        """Open file explorer for folder selection."""
        folder = filedialog.askdirectory(title="Select folder for deletion")
        if folder:
            self.selected_path = folder
            self.path_display.config(text=folder)

    def delete_now(self):
        """Immediately delete selected file (No scheduling)."""
        if not self.selected_path or os.path.isdir(self.selected_path):
            messagebox.showerror("Error", "Please select a single file for immediate deletion!")
            return

        terminate_related_processes(self.selected_path)
        if self.secure_delete_enabled.get():
            secure_delete(self.selected_path)
        else:
            os.remove(self.selected_path)
            logging.info(f"File '{self.selected_path}' deleted without secure overwrite.")

        messagebox.showinfo("Success", "File deleted securely!")

    def start_scheduled_deletion(self):
        """Start auto-deletion process only if a folder is selected."""
        if not self.selected_path or not os.path.isdir(self.selected_path):
            messagebox.showerror("Error", "Please select a folder for scheduled deletion!")
            return

        self.progress.start()
        interval = self.interval_var.get()
        self.scheduled_task = threading.Timer(interval, self.auto_delete_folder)  # Delete every 'interval' seconds
        self.scheduled_task.start()
        messagebox.showinfo("Started", f"Auto-deletion initiated for folder every {interval} seconds!")

    def stop_scheduled_deletion(self):
        """Stop scheduled deletion."""
        if self.scheduled_task:
            self.scheduled_task.cancel()
            self.progress.stop()
            messagebox.showinfo("Stopped", "Auto-deletion stopped!")

    def auto_delete_folder(self):
        """Delete all files in the selected folder in the background."""
        for file in os.listdir(self.selected_path):
            file_path = os.path.join(self.selected_path, file)
            terminate_related_processes(file_path)
            if self.secure_delete_enabled.get():
                secure_delete(file_path)
            else:
                os.remove(file_path)
                logging.info(f"File '{file_path}' deleted without secure overwrite.")

        self.progress.stop()
        interval = self.interval_var.get()
        messagebox.showinfo("Completed", f"Auto-deletion completed! Restarting in {interval} seconds.")
        self.scheduled_task = threading.Timer(interval, self.auto_delete_folder)
        self.scheduled_task.start()

if __name__ == "__main__":
    app = BootstrapGUI()
    app.mainloop()
