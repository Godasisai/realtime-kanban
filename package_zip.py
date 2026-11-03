import os
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ZIP_NAME = "Julley_RealTime_Kanban_Assignment_Sai_Ammanna_Naidu.zip"
OUTPUT_PATH = BASE_DIR / ZIP_NAME

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
}

EXCLUDE_FILES = {
    ZIP_NAME,
    "kanban.db-shm",
    "kanban.db-wal",
}


def create_submission_zip():
    print(f"Packaging project into: {OUTPUT_PATH}")
    file_count = 0

    with zipfile.ZipFile(OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                if file in EXCLUDE_FILES or file.endswith(".pyc"):
                    continue

                full_path = Path(root) / file
                arcname = full_path.relative_to(BASE_DIR)
                zipf.write(full_path, arcname)
                file_count += 1

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"[OK] Submission ZIP created successfully!")
    print(f"Archive: {OUTPUT_PATH}")
    print(f"Files included: {file_count}")
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    create_submission_zip()
