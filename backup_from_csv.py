import os
import shutil
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

CSV_PATH = 'C:/Users/username/input/pdf_log.csv'
ALLOWED_EXT = {'.py', '.vba', '.md', '.docx', '.xlsx', '.pdf', '.ps1'}
BACKUP_ROOT = Path("C:/Users/username/backup/output")

NOW = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_NAME = f"archive-{NOW}"
BACKUP_FOLDER = BACKUP_ROOT / BACKUP_NAME
ZIP_PATH = BACKUP_ROOT / f"{BACKUP_NAME}.zip"

log_path = BACKUP_ROOT / "backup_log.txt"
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("=== Backup Run Started ===")

def is_valid_file(file_path: str) -> bool:
    try:
        ext = Path(file_path).suffix.lower()
        return ext in ALLOWED_EXT and Path(file_path).exists()
    except Exception as e:
        logging.error(f"Validation failed: {file_path} => {e}")
        return False

def copy_preserving_structure(src_path: Path, root_folder: Path):
    try:
        rel_path = src_path.drive + src_path.as_posix()[2:]
        rel = Path(rel_path).relative_to(Path(src_path.drive + "/"))
        dest_path = root_folder / rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)
        logging.info(f"Copied: {src_path} -> {dest_path}")
        return True
    except PermissionError as pe:
        logging.error(f"Permission denied: {src_path} => {pe}")
    except Exception as e:
        logging.error(f"Copy failed: {src_path} => {e}")
    return False

def main():
    try:
        df = pd.read_csv(CSV_PATH)
        if 'file_path' not in df.columns:
            raise ValueError("Missing required 'file_path' column in CSV.")
    except Exception as e:
        print(f"Failed to load CSV: {e}")
        logging.critical(f"CSV load error: {e}")
        return

    print(f"Starting full backup to: {BACKUP_FOLDER}")
    copied, skipped, failed = 0, 0, 0

    for _, row in df.iterrows():
        try:
            raw_path = str(row['file_path']).strip()
            src = Path(raw_path)

            if is_valid_file(src):
                if copy_preserving_structure(src, BACKUP_FOLDER):
                    copied += 1
                else:
                    failed += 1
            else:
                logging.warning(f"Skipped (invalid or missing): {raw_path}")
                skipped += 1
        except Exception as e:
            logging.error(f"Unexpected error during row processing: {e}")
            failed += 1

    try:
        print("Creating ZIP archive...")
        shutil.make_archive(str(ZIP_PATH).replace('.zip', ''), 'zip', BACKUP_FOLDER)
        logging.info(f"Backup zipped: {ZIP_PATH}")
        print(f"Backup complete: {ZIP_PATH}")
    except Exception as e:
        logging.error(f"ZIP failed: {e}")
        print(f"ZIP creation failed: {e}")
    logging.info("Backup process completed.")
    print("Backup process completed.")
    print("=== Summary ===")
    logging.info("=== Summary ===")
    print(f"Copied: {copied}, Skipped: {skipped}, Failed: {failed}")
    logging.info(f"Copied: {copied}, Skipped: {skipped}, Failed: {failed}")
    summary = f"Copied: {copied}, Skipped: {skipped}, Failed: {failed}"
    print(summary)
    logging.info(summary)
    logging.info("=== Backup Run Completed ===\n")

if __name__ == "__main__":
    main()
