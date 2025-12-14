#!/usr/bin/python3
# -*- coding:utf-8 -*-

import argparse
import sqlite3

db_name = "note.db"


def get_db_connection():
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


def command_list(args):
    filters = []
    values = []
    conn = get_db_connection()

    if args.date:
        filters.append("DATE(date) = ?")
        values.append(args.date)
    if args.note_type:
        filters.append("type = ?")
        values.append(args.note_type)

    query = "SELECT * FROM notes"

    if filters:
        query += " WHERE " + " AND ".join(filters)

    c = conn.cursor()
    if filters:
        c.execute(query, tuple(values))
    else:
        c.execute("SELECT * FROM notes;")

    notes = c.fetchall()
    for i in notes:
        print('"{}", "{}", "{}", "{}"'.format(i["id"], i["date"], i["note"], i["type"]))
    c.close()
    conn.close()


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
