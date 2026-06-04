#!/usr/bin/env python3
"""Deploy the morning briefing to docs/ for GitHub Pages.

Usage:
    python deploy.py                          # deploy latest brief-today.html
    python deploy.py --source custom.html     # deploy a specific file
    python deploy.py --archive               # archive without updating latest

This copies the rendered brief into docs/latest.html and docs/archive/YYYY-MM-DD.html,
then commits and pushes to GitHub Pages (docs/ folder on main branch).
"""

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DOCS = REPO_ROOT / "docs"
ARCHIVE = DOCS / "archive"
SOURCE = REPO_ROOT / "brief-today.html"


def ensure_dirs():
    ARCHIVE.mkdir(parents=True, exist_ok=True)


def deploy(source_path: Path, archive_only: bool = False) -> bool:
    ensure_dirs()

    today = date.today()
    archive_name = f"{today.isoformat()}.html"
    archive_path = ARCHIVE / archive_name

    # Copy to archive
    shutil.copy2(source_path, archive_path)
    print(f"Archived: {archive_path.relative_to(REPO_ROOT)}")

    if not archive_only:
        # Copy as latest
        latest_path = DOCS / "latest.html"
        shutil.copy2(source_path, latest_path)
        print(f"Latest:   {latest_path.relative_to(REPO_ROOT)}")

    # Git operations
    os.chdir(str(REPO_ROOT))
    result = subprocess.run(
        ["git", "add", "docs/"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"git add error: {result.stderr.strip()}")
        return False

    result = subprocess.run(
        ["git", "commit", "-m", f"deploy: brief for {today}"],
        capture_output=True, text=True
    )
    if result.returncode != 0 and "nothing to commit" not in result.stdout:
        print(f"git commit: {result.stdout.strip()}")
        print(f"git commit stderr: {result.stderr.strip()}")

    result = subprocess.run(
        ["git", "push"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"git push error: {result.stderr.strip()}")
        return False

    print(f"Pushed to GitHub. Page: https://briefing.acolod.com/")
    return True


if __name__ == "__main__":
    import os

    source = SOURCE
    archive_only = False

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--source" and i + 1 < len(args):
            source = Path(args[i + 1])
        elif arg == "--archive":
            archive_only = True

    if not source.exists():
        print(f"Source not found: {source}")
        print("Run the briefing pipeline first, or use --source to point to a file.")
        sys.exit(1)

    success = deploy(source, archive_only=archive_only)
    sys.exit(0 if success else 1)