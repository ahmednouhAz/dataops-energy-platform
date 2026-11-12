"""Tiny tool to query the warehouse in read-only mode (TP3 pattern).

    python query.py "select * from raw.eco2mix_regional limit 5"
"""
import os
import sys

import duckdb

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dev.duckdb")

if __name__ == "__main__":
    # Windows' default console encoding (cp1252) can't print DuckDB's box-drawing
    # table output; force UTF-8 on stdout regardless of platform.
    sys.stdout.reconfigure(encoding="utf-8")
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    con.sql(sys.argv[1]).show()
