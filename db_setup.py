import datetime
import sqlite3

dbname = "note.db"

conn = sqlite3.connect(dbname)
c = conn.cursor()
c.execute(
    "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, date TEXT, note TEXT, type TEXT)"
)

now = datetime.datetime.now()
c.execute(
    "INSERT INTO notes(date, note, type) VALUES (?, ?, ?)",
    (now.strftime("%Y-%m-%d %H:%M:%S"), "sample", "note"),
)

conn.commit()
conn.close()
