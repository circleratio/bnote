#!/usr/bin/python3
"""Back up the bnote database with the SQLite online backup API.

Environment variables:
    BNOTE_DB            database to back up (default: note.db next to this file)
    BNOTE_BACKUP_DIR    output directory (default: backups/ next to the database)
    BNOTE_BACKUP_KEEP   number of backups to keep (default: 14)
"""

import datetime
import os
import sqlite3
import sys
from pathlib import Path

PREFIX = "note-"
SUFFIX = ".db"


def main() -> int:
    db_path = Path(
        os.environ.get("BNOTE_DB", Path(__file__).resolve().parent / "note.db")
    )
    backup_dir = Path(os.environ.get("BNOTE_BACKUP_DIR", db_path.parent / "backups"))
    keep = int(os.environ.get("BNOTE_BACKUP_KEEP", "14"))
    if keep < 1:
        print("BNOTE_BACKUP_KEEP must be 1 or more", file=sys.stderr)
        return 1
    if not db_path.is_file():
        print(f"database not found: {db_path}", file=sys.stderr)
        return 1

    os.umask(0o077)
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"{PREFIX}{stamp}{SUFFIX}"
    tmp = dest.with_name(dest.name + ".tmp")

    # Open the source read-only so the backup job can never modify it.
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst)
            result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            dst.close()
    finally:
        src.close()

    if result != "ok":
        tmp.unlink(missing_ok=True)
        print(f"integrity check failed: {result}", file=sys.stderr)
        return 1

    # Publish the backup atomically so a half-written file is never kept.
    tmp.replace(dest)
    print(f"backup written: {dest}")

    # Remove leftovers of interrupted runs and backups beyond the retention count.
    for stale in backup_dir.glob(f"{PREFIX}*{SUFFIX}.tmp"):
        stale.unlink(missing_ok=True)
    backups = sorted(backup_dir.glob(f"{PREFIX}*{SUFFIX}"))
    for old in backups[:-keep]:
        old.unlink()
        print(f"backup removed: {old}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
