import datetime
import os
import sqlite3
from pathlib import Path

dbname = str(Path(__file__).resolve().parent / "note.db")

conn = sqlite3.connect(dbname)
c = conn.cursor()
c.execute(
    "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, date TEXT, note TEXT, type TEXT)",
)

now = datetime.datetime.now()
c.execute(
    "INSERT INTO notes(date, note, type) VALUES (?, ?, ?)",
    (now.strftime("%Y-%m-%d %H:%M:%S"), "sample", "note"),
)

conn.commit()
conn.close()

# Restrict the database file to the owner only.
os.chmod(dbname, 0o600)
