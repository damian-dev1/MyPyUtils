import os
import shutil
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

CSV_PATH = 'C:/Users/damian/projects/llm-gui/test/backup/input/pdf_log.csv'  # Must include a 'file_path' column
ALLOWED_EXT = {'.py', '.vba', '.md', '.docx', '.xlsx', '.pdf', '.ps1'}
BACKUP_ROOT = Path("C:/Users/damian/projects/llm-gui/test/backup/output")
NOW = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_NAME = f"python-files-{NOW}"
BACKUP_FOLDER = BACKUP_ROOT / BACKUP_NAME
ZIP_PATH = BACKUP_ROOT / f"{BACKUP_NAME}.zip"

log_path = BACKUP_ROOT / "backup_log.txt"
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def is_valid_file(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in ALLOWED_EXT and Path(file_path).exists()

def copy_preserving_structure(src_path: Path, root_folder: Path):
    try:
        rel_path = Path(src_path.drive + src_path.as_posix()[2:]).relative_to(Path(src_path.drive + "/"))
        dest_path = root_folder / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)
        logging.info(f"Copied: {src_path} -> {dest_path}")
    except Exception as e:
        logging.error(f"Failed: {src_path} => {e}")

def main():
    df = pd.read_csv(CSV_PATH)
    if 'file_path' not in df.columns:
        print("ERROR: 'file_path' column not found in CSV.")
        return

    print(f"Backup started: {BACKUP_NAME}")
    for _, row in df.iterrows():
        raw_path = row['file_path']
        src = Path(raw_path)
        if is_valid_file(src):
            copy_preserving_structure(src, BACKUP_FOLDER)
        else:
            logging.warning(f"Skipped or invalid: {raw_path}")

    print("Creating ZIP archive...")
    shutil.make_archive(str(ZIP_PATH).replace('.zip', ''), 'zip', BACKUP_FOLDER)
    print(f"Backup complete: {ZIP_PATH}")
    logging.info(f"Backup archive created: {ZIP_PATH}")

if __name__ == "__main__":
    main()
