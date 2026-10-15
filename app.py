"""CLI: answer a natural-language question about the sales/inventory database.

Usage:
    python app.py "What is the total revenue?"
    python app.py --interactive

Prints the generated SQL, runs it against data/sales.db, and prints results.
"""
import argparse
import sqlite3
import sys

from schema import get_schema
from text_to_sql import get_llm

DB_PATH = "data/sales.db"


def answer(question: str) -> str:
    llm = get_llm()
    sql = llm.generate_sql(question, get_schema())
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(sql).fetchall()
    finally:
        con.close()

    lines = [f"Question: {question}", f"SQL: {sql}"]
    if not rows:
        lines.append("(no rows returned)")
    else:
        lines.append(" | ".join(rows[0].keys()))
        for r in rows:
            lines.append(" | ".join(str(v) for v in r))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Natural-language analytics over sales.db")
    parser.add_argument("question", nargs="?", help="question to answer")
    parser.add_argument("--interactive", action="store_true", help="prompt loop")
    args = parser.parse_args()

    if args.interactive:
        print("Ask questions about sales/inventory (empty line quits).")
        while True:
            q = input("> ").strip()
            if not q:
                break
            try:
                print(answer(q))
            except Exception as exc:  # noqa: BLE001 - CLI should not crash
                print(f"Error: {exc}")
    elif args.question:
        try:
            print(answer(args.question))
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
