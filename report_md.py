"""Print fct_energy_production as a Markdown table, and stop if the total
differs from the expected one (TP4 pattern: a regression test against a
known reference number on the CI sample).
"""
import os
import sys

import duckdb

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dev.duckdb")


def main(expected=None):
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    rows = con.sql(
        "select energy_source, round(sum(production_mw), 2) as total_mw, count(*) as n"
        " from fct_energy_production group by 1 order by 1"
    ).fetchall()
    total = round(sum(float(total_mw) for _, total_mw, _ in rows), 2)
    n_rows = sum(n for _, _, n in rows)

    print("| Energy source | Total MW | Rows |")
    print("| --- | ---: | ---: |")
    for source, total_mw, n in rows:
        print(f"| {source} | {float(total_mw):.2f} | {n} |")
    print(f"\n**Total: {total:.2f} MW over {n_rows} rows**")

    if expected is not None and total != expected:
        print(f"\nREGRESSION: expected {expected:.2f}, got {total:.2f}")
        sys.exit(1)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else None)
