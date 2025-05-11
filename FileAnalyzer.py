import os
import pathlib
import hashlib
import mimetypes
import json
from datetime import datetime

def select_folder():
    folder_path = input("\nEnter the path to the folder you want to scan: ").strip()
    folder = pathlib.Path(folder_path)
    if not folder.is_dir():
        raise ValueError("Invalid folder path!")
    return folder

def list_files(folder):
    files = [f for f in folder.iterdir() if f.is_file()]
    if not files:
        print("No files found in the selected folder.")
        exit()
    print("\nFiles found:")
    for idx, file in enumerate(files, start=1):
        print(f"{idx}: {file.name}")
    return files

def select_file(files):
    choice = int(input("\nEnter the number of the file you want to analyze: "))
    if choice < 1 or choice > len(files):
        raise ValueError("Invalid choice!")
    return files[choice - 1]

def calculate_entropy(file_path):
    """Calculate file entropy (randomness of bytes)"""
    with open(file_path, "rb") as f:
        data = f.read()
    if not data:
        return 0.0
    import math
    byte_freq = [0] * 256
    for byte in data:
        byte_freq[byte] += 1
    entropy = 0
    for freq in byte_freq:
        if freq > 0:
            p = freq / len(data)
            entropy -= p * math.log2(p)
    return round(entropy, 4)

def analyze_file(file_path):
    info = {}
    stat = file_path.stat()

    # Basic Info
    info['Name'] = file_path.name
    info['Absolute Path'] = str(file_path.absolute())
    info['Parent Folder'] = str(file_path.parent)
    info['Size (bytes)'] = stat.st_size
    info['Created'] = datetime.fromtimestamp(stat.st_ctime).isoformat()
    info['Modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    info['File Extension'] = file_path.suffix
    info['MIME Type'] = mimetypes.guess_type(file_path)[0] or "Unknown"

    # Access Permissions
    info['Is Readable'] = os.access(file_path, os.R_OK)
    info['Is Writable'] = os.access(file_path, os.W_OK)
    try:
        info['Permissions (Octal)'] = oct(stat.st_mode)[-3:]
    except Exception:
        info['Permissions (Octal)'] = "N/A"

    # File Owner (Linux/macOS only)
    if os.name != 'nt':
        import pwd
        try:
            info['Owner'] = pwd.getpwuid(stat.st_uid).pw_name
        except Exception:
            info['Owner'] = "Unknown"
    else:
        info['Owner'] = "Not available on Windows"

    # Hash
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    info['SHA-256'] = sha256_hash.hexdigest()

    # Entropy
    info['Entropy'] = calculate_entropy(file_path)

    # Line/Word Count for Text Files
    mime_type = info['MIME Type']
    if mime_type and "text" in mime_type:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            info['Line Count'] = len(lines)
            info['Word Count'] = sum(len(line.split()) for line in lines)
        except Exception:
            info['Line Count'] = "N/A"
            info['Word Count'] = "N/A"

    return info

def example_usage(extension):
    usage_examples = {
        '.py': "Python script - used for automation, backend systems, data analysis.",
        '.jpg': "JPEG image - used for web images, digital photography.",
        '.docx': "Word Document - used for reports, resumes, documentation.",
        '.xlsx': "Excel spreadsheet - used for data analysis, reports.",
        '.mp3': "MP3 audio - used for music, podcasts.",
        '.pdf': "PDF document - used for manuals, brochures, contracts.",
        '.exe': "Executable file - runs a program or application on Windows.",
        '.zip': "Compressed archive - used to bundle files together.",
    }
    return usage_examples.get(extension.lower(), "No usage example available for this file type.")

def export_info(file_info):
    export_path = input("\nEnter the path and filename to export info (e.g., report.json): ").strip()
    try:
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(file_info, f, indent=4)
        print(f"✅ File information exported successfully to {export_path}")
    except Exception as e:
        print(f"❌ Failed to export file information: {e}")

def main():
    print("\n📂 Welcome to Verbose File Analyzer 📂\n")
    current_folder = select_folder()
    files = list_files(current_folder)
    last_file_info = None

    while True:
        try:
            selected_file = select_file(files)

            print("\n🔍 Analyzing file in verbose mode, please wait...\n")
            last_file_info = analyze_file(selected_file)

            print("\n📄 Verbose File Information:")
            for key, value in last_file_info.items():
                print(f"{key}: {value}")

            usage = example_usage(last_file_info['File Extension'])
            print(f"\n💡 Example Usage: {usage}")

            print("\nWhat would you like to do next?")
            print("1. 📂 Select another folder")
            print("2. 📄 Select another file from the same folder")
            print("3. 📝 Export this file info")
            print("4. ❌ Exit the program")

            action = input("\nEnter your choice (1-4): ").strip()

            if action == '1':
                current_folder = select_folder()
                files = list_files(current_folder)
            elif action == '2':
                files = list_files(current_folder)  # re-list just in case new files added
            elif action == '3':
                if last_file_info:
                    export_info(last_file_info)
                else:
                    print("⚠️ No file analyzed yet.")
            elif action == '4':
                print("\n👋 Thank you for using Verbose File Analyzer. Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select a valid option (1-4).")

        except Exception as e:
            print(f"⚠️ Error: {e}")
            continue

if __name__ == "__main__":
    main()
