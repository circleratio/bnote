#!/usr/bin/python3
"""A simple note application with Python/bottle.
"""

import datetime
import re
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

from bottle import redirect, request, route, run, static_file, template
from dateutil.relativedelta import relativedelta

BASE_DIR = str(Path(__file__).resolve().parent)
STATIC_DIR = Path(BASE_DIR) / "static"
TIMEZONE = "Asia/Tokyo"

db_name = "note.db"
base_url = "http://localhost:8080" if __name__ == "__main__" else "/bnote"

def _get_db_connection():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


def _quote_url(text: str) -> str:
    url_pattern = r"https?://[\w.?=&#%~/-]+"

    def _replace_with_link(match) -> str:
        url = match.group(0)
        return f'<a href="{url}">{url}</a>'

    return(re.sub(url_pattern, _replace_with_link, text))


def _days_before_and_after(date_str: str) -> list[str, str]:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        dt = datetime.datetime(year, month, day, 0, 0, 0, 0,
                               tzinfo=ZoneInfo(TIMEZONE))

        day_before = dt + relativedelta(days=-1)
        day_after = dt + relativedelta(days=+1)
        day_before_s = day_before.strftime("%Y-%m-%d")
        day_after_s = day_after.strftime("%Y-%m-%d")

        return (day_before_s, day_after_s)
    return (None, None)


@route("/static/<filepath:path>")
def server_static(filepath: str):
    """Securely and efficiently serve static assets to the client."""
    return static_file(filepath, root=f"{STATIC_DIR}")


@route("/")
def index() -> str:
    """Show the landing page."""
    return template("new", note="", base_url=base_url)


@route("/new")
def new_note() -> str:
    """Show a editor page for a new note."""
    return template("new", note="", base_url=base_url)


@route("/add", method="POST")
def add_note() -> str:
    """Add a new note."""
    note = request.forms.getunicode("note")
    note = note.replace("\r", "")
    note_id = int(request.forms.getunicode("note_id"))
    note_type = request.forms.getunicode("note_type")
    now = datetime.datetime.now(ZoneInfo(TIMEZONE))
    now_s = now.strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_db_connection()
    c = conn.cursor()
    if note_id == -1:
        c.execute(
            "INSERT INTO notes(date, note, type) VALUES (?, ?, ?);",
            (now_s, note, note_type),
        )
    else:
        c.execute(
            "UPDATE notes SET (date, note, type) = (?, ?, ?) WHERE id=?;",
            (now_s, note, note_type, note_id),
        )
    conn.commit()
    c.close()
    conn.close()
    return template("new", item_id=-1, note="", base_url=base_url)


@route("/list-all")
def get_list_all() -> str:
    """Get a list of all notes."""
    conn = _get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes;")
    notes = c.fetchall()
    c.close()
    conn.close()
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=_quote_url,
        prev_link=None,
        next_link=None,
    )


@route("/list")
def get_list_today() -> str:
    """Get a list of note for today."""
    today = datetime.datetime.now(ZoneInfo(TIMEZONE))
    pat = today.strftime("%Y-%m-%d")

    prev_link, next_link = _days_before_and_after(pat)

    conn = _get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE DATE(date) = ?;", (pat,))
    notes = c.fetchall()
    c.close()
    conn.close()
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=_quote_url,
        prev_link=prev_link,
        next_link=next_link,
    )


@route("/list/<date_str>")
def get_list_by_date(date_str: str) -> str:
    """Get a list of note for the specified date.

    Args:
        date_str: a string in the format YYYY-MM-DD

    """
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m is None:
        return template("404", base_url=base_url)

    prev_link, next_link = _days_before_and_after(date_str)

    conn = _get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE DATE(date) = ?;", (date_str,))

    notes = c.fetchall()
    c.close()
    conn.close()
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=_quote_url,
        prev_link=prev_link,
        next_link=next_link,
    )


@route("/edit/<item_id:int>")
def edit_note(item_id: int) -> str:
    """Edit a note.

    Args:
        item_id: database id for a note

    """
    conn = _get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes where id=?;", (item_id,))
    notes = c.fetchall()
    c.close()
    conn.close()

    if len(notes) == 1:
        note = notes[0]["note"]

    return template("edit", item_id=item_id, note=note, base_url=base_url)


@route("/delete/<item_id:int>")
def delete_note(item_id :int) -> None:
    """Delete a note.

    Args:
        item_id: database id for a note

    """
    conn = _get_db_connection()
    c = conn.cursor()

    c.execute("DELETE FROM notes where id=?;", (item_id,))
    conn.commit()

    c.close()
    conn.close()

    redirect(f"{base_url}/list")


if __name__ == "__main__":
    #run(host="localhost", port=8080, debug=True)
    print(get_list_today())
