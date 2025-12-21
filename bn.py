#!/usr/bin/python3
# -*- coding:utf-8 -*-

import argparse
import sqlite3
import datetime
import os
import re

work_dir = os.path.dirname(os.path.abspath(__file__))
db_name = f"{work_dir}/note.db"


def get_db_connection():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


def exec_query(date, note_type):
    filters = []
    values = []
    conn = get_db_connection()

    if date:
        m = re.match('(\d{4})(\d{2})(\d{2})', date)
        if m:
            date = '{}-{}-{}'.format(m.group(1), m.group(2), m.group(3))
        
        filters.append("DATE(date) = ?")
        values.append(date)
    if note_type:
        filters.append("type = ?")
        values.append(note_type)

    query = "SELECT * FROM notes"

    if filters:
        query += " WHERE " + " AND ".join(filters)

    c = conn.cursor()
    if filters:
        c.execute(query, tuple(values))
    else:
        c.execute("SELECT * FROM notes;")

    notes = c.fetchall()
    c.close()
    conn.close()

    return notes


def today_str():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d")


def command_list(args):
    notes = exec_query(args.date, args.note_type)
    for i in notes:
        ripped = "".join(i["note"].splitlines())
        print('"{}", "{}", "{}", "{}"'.format(i["id"], i["date"], ripped, i["type"]))


def command_markdown(args):
    if args.date == None:
        args.date = today_str()

    notes = exec_query(args.date, "note")

    print("---\ndate: {}\n---".format(args.date.replace("-", ".")))
    for i in notes:
        print(f"#\n{i['note']}\n")


def command_add(args):
    print(args)


def command_update(args):
    print(args)


def command_delete(args):
    print(args)


def command_help(args):
    print(parser.parse_args([args.command, "--help"]))


def main():
    parser = argparse.ArgumentParser(description="note management")
    subparsers = parser.add_subparsers()

    parser_list = subparsers.add_parser("list", help="see `list -h`")
    parser_list.add_argument(
        "-d", "--date", type=str, help="filter by date (YYYY-MM-DD)"
    )
    parser_list.add_argument("-t", "--note_type", type=str, help="filter by type")
    parser_list.set_defaults(handler=command_list)

    parser_md = subparsers.add_parser("md", help="see `list -h`")
    parser_md.add_argument("-d", "--date", type=str, help="specify date (YYYY-MM-DD)")
    parser_md.set_defaults(handler=command_markdown)

    parser_add = subparsers.add_parser("add", help="see `add -h`")
    parser_add.add_argument("-A", "--all", action="store_true", help="all files")
    parser_add.set_defaults(handler=command_add)

    parser_update = subparsers.add_parser("update", help="see `update -h`")
    parser_update.add_argument("-m", metavar="msg", help="update message")
    parser_update.set_defaults(handler=command_update)

    parser_delete = subparsers.add_parser("delete", help="see `delete -h`")
    parser_delete.add_argument("-m", metavar="msg", help="delete message")
    parser_delete.set_defaults(handler=command_delete)

    parser_help = subparsers.add_parser("help", help="see `help -h`")
    parser_help.add_argument("command", help="command name which help is shown")
    parser_help.set_defaults(handler=command_help)

    args = parser.parse_args()
    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
