#!/usr/bin/python3
# -*- coding:utf-8 -*-

import datetime
import os
import re
import sqlite3

from bottle import request, route, run, static_file, template, redirect
from dateutil.relativedelta import relativedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

db_name = "note.db"
if __name__ == "__main__":
    base_url = "http://localhost:8080"
else:
    base_url = "/bnote"


def get_db_connection():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


def quote_url(text):
    url_pattern = r"https?://[\w.?=&#%~/-]+"

    def replace_with_link(match):
        url = match.group(0)
        return f'<a href="{url}">{url}</a>'

    linked_text = re.sub(url_pattern, replace_with_link, text)
    return linked_text


def days_before_and_after(date_str):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        dt = datetime.date(year, month, day)

        day_before = dt + relativedelta(days=-1)
        day_after = dt + relativedelta(days=+1)
        day_before_s = day_before.strftime("%Y-%m-%d")
        day_after_s = day_after.strftime("%Y-%m-%d")

        return (day_before_s, day_after_s)
    else:
        return (None, None)


@route("/static/<filepath:path>")
def server_static(filepath):
    return static_file(filepath, root=f"{STATIC_DIR}")


@route("/")
def index():
    return template("new", note="", base_url=base_url)


@route("/new")
def new_note():
    return template("new", note="", base_url=base_url)


@route("/add", method="POST")
def add_note():
    note = request.forms.getunicode("note")
    note = note.replace("\r", "")
    note_id = int(request.forms.getunicode("note_id"))
    note_type = request.forms.getunicode("note_type")
    now = datetime.datetime.now()
    now_s = now.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
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
def get_list_all():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes;")
    notes = c.fetchall()
    c.close()
    conn.close()
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=quote_url,
        prev_link=None,
        next_link=None,
    )


@route("/list")
def get_list_today():
    today = datetime.datetime.now()
    pat = today.strftime("%Y-%m-%d")

    prev_link, next_link = days_before_and_after(pat)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE DATE(date) = ?;", (pat,))
    notes = c.fetchall()
    c.close()
    conn.close()
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=quote_url,
        prev_link=prev_link,
        next_link=next_link,
    )


@route("/list/<date_str>")
def get_list_by_date(date_str):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m is None:
        return template("404", base_url=base_url)

    prev_link, next_link = days_before_and_after(date_str)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE DATE(date) = ?;", (date_str,))

    notes = c.fetchall()
    c.close()
    conn.close()
    return template(
        "list",
        notes=notes,
        base_url=base_url,
        formatter=quote_url,
        prev_link=prev_link,
        next_link=next_link,
    )


@route("/edit/<item_id:int>")
def edit_note(item_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM notes where id=?;", (item_id,))
    notes = c.fetchall()
    c.close()
    conn.close()

    if len(notes) == 1:
        note = notes[0]["note"]

    return template("edit", item_id=item_id, note=note, base_url=base_url)


@route("/delete/<item_id:int>")
def delete_note(item_id):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("DELETE FROM notes where id=?;", (item_id,))
    conn.commit()

    c.close()
    conn.close()

    redirect(f"{base_url}/list")


if __name__ == "__main__":
    run(host="localhost", port=8080, debug=True)
