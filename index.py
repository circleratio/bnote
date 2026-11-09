#!/usr/bin/python3
"""A simple note application with Python/bottle."""

import datetime
import html
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

from bottle import (
    HTTPResponse,
    abort,
    hook,
    install,
    redirect,
    request,
    response,
    route,
    run,
    static_file,
    template,
)
from dateutil.relativedelta import relativedelta

BASE_DIR = str(Path(__file__).resolve().parent)
STATIC_DIR = Path(BASE_DIR) / "static"
TIMEZONE = "Asia/Tokyo"

db_name = str(Path(BASE_DIR) / "note.db")
PAGE_SIZE = 50
NOTE_TYPES = ("note", "action")
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; frame-ancestors 'none'; form-action 'self'"
    ),
    # "no-referrer" would make browsers send "Origin: null" on POST,
    # which breaks the CSRF check below.
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
}
#base_url = "http://localhost:8080" if __name__ == "__main__" else "/bnote"
base_url = "https://note.circleratio314.com" if __name__ == "__main__" else "/bnote"


def _get_db_connection():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


def _quote_url(text: str) -> str:
    escaped = html.escape(text)
    url_pattern = r"https?://[\w.?=&;#%~/-]+"

    def _replace_with_link(match) -> str:
        url = match.group(0)
        return f'<a href="{url}" rel="noreferrer noopener">{url}</a>'

    return re.sub(url_pattern, _replace_with_link, escaped)


def _is_valid_date(date_str: str) -> bool:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str) is None:
        return False
    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        return False
    return True


def _not_found() -> str:
    response.status = 404
    return template("404", base_url=base_url)


def _set_security_headers(resp) -> None:
    for name, value in SECURITY_HEADERS.items():
        resp.set_header(name, value)


def _security_headers_plugin(callback):
    """Add security headers to every response, including redirects and errors."""

    def wrapper(*args, **kwargs):
        try:
            body = callback(*args, **kwargs)
        except HTTPResponse as resp:
            _set_security_headers(resp)
            raise
        _set_security_headers(body if isinstance(body, HTTPResponse) else response)
        return body

    return wrapper


install(_security_headers_plugin)


@hook("before_request")
def _check_same_origin() -> None:
    """Reject cross-site POST requests (CSRF protection).

    The host in Origin (or Referer as a fallback) must match the request host.
    Behind a reverse proxy, the proxy must pass the original Host header or
    X-Forwarded-Host.
    """
    if request.method != "POST":
        return
    source = request.headers.get("Origin") or request.headers.get("Referer")
    if not source or urlsplit(source).netloc != request.urlparts.netloc:
        abort(403, "Cross-site request rejected.")


def _days_before_and_after(date_str: str) -> list[str, str]:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        dt = datetime.datetime(year, month, day, 0, 0, 0, 0, tzinfo=ZoneInfo(TIMEZONE))

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
    if note is None:
        abort(400, "Missing note.")
    note = note.replace("\r", "")
    try:
        note_id = int(request.forms.getunicode("note_id"))
    except (TypeError, ValueError):
        abort(400, "Invalid note_id.")
    note_type = request.forms.getunicode("note_type")
    if note_type not in NOTE_TYPES:
        abort(400, "Invalid note_type.")
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
    """Get a paginated list of all notes, newest first."""
    try:
        page = max(1, int(request.query.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    conn = _get_db_connection()
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM notes;").fetchone()[0]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    offset = (page - 1) * PAGE_SIZE
    c.execute(
        "SELECT * FROM notes ORDER BY id DESC LIMIT ? OFFSET ?;",
        (PAGE_SIZE, offset),
    )
    notes = c.fetchall()
    c.close()
    conn.close()

    prev_link = f"{base_url}/list-all?page={page - 1}" if page > 1 else None
    next_link = f"{base_url}/list-all?page={page + 1}" if page < total_pages else None
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=_quote_url,
        prev_link=prev_link,
        next_link=next_link,
        page=page,
        total_pages=total_pages,
    )


@route("/search")
def search_notes() -> str:
    """Search notes whose body contains the keyword, newest first, paginated."""
    q = request.query.getunicode("q", "").strip()
    try:
        page = max(1, int(request.query.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    if not q:
        return template(
            "list",
            notes=[],
            base_url=base_url,
            formatter=_quote_url,
            prev_link=None,
            next_link=None,
            page=None,
            total_pages=None,
            q="",
        )

    # Escape LIKE wildcards so the keyword is matched literally.
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like = f"%{escaped}%"

    conn = _get_db_connection()
    c = conn.cursor()
    total = c.execute(
        "SELECT COUNT(*) FROM notes WHERE note LIKE ? ESCAPE '\\';",
        (like,),
    ).fetchone()[0]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    offset = (page - 1) * PAGE_SIZE
    c.execute(
        "SELECT * FROM notes WHERE note LIKE ? ESCAPE '\\' "
        "ORDER BY id DESC LIMIT ? OFFSET ?;",
        (like, PAGE_SIZE, offset),
    )
    notes = c.fetchall()
    c.close()
    conn.close()

    qs = quote(q)
    prev_link = (
        f"{base_url}/search?q={qs}&page={page - 1}" if page > 1 else None
    )
    next_link = (
        f"{base_url}/search?q={qs}&page={page + 1}" if page < total_pages else None
    )
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=_quote_url,
        prev_link=prev_link,
        next_link=next_link,
        page=page,
        total_pages=total_pages,
        q=q,
    )


@route("/list")
def get_list_today() -> str:
    """Get a list of note for today."""
    today = datetime.datetime.now(ZoneInfo(TIMEZONE))
    pat = today.strftime("%Y-%m-%d")

    prev_date, next_date = _days_before_and_after(pat)

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
        prev_link=f"{base_url}/list/{prev_date}" if prev_date else None,
        next_link=f"{base_url}/list/{next_date}" if next_date else None,
        page=None,
        total_pages=None,
    )


@route("/list/<date_str>")
def get_list_by_date(date_str: str) -> str:
    """Get a list of note for the specified date.

    Args:
        date_str: a string in the format YYYY-MM-DD

    """
    if not _is_valid_date(date_str):
        return _not_found()

    prev_date, next_date = _days_before_and_after(date_str)

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
        prev_link=f"{base_url}/list/{prev_date}" if prev_date else None,
        next_link=f"{base_url}/list/{next_date}" if next_date else None,
        page=None,
        total_pages=None,
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

    if len(notes) != 1:
        return _not_found()
    note = notes[0]["note"]

    return template("edit", item_id=item_id, note=note, base_url=base_url)


@route("/delete/<item_id:int>", method="POST")
def delete_note(item_id: int) -> None:
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
    run(host="localhost", port=8080, debug=False)
