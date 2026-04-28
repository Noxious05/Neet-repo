"""
Export sample data showing the database schema and contents.

Output:
    data/sample/colleges.csv               — all colleges
    data/sample/cutoffs_<quota>_<year>.csv — one CSV per quota×year split
    data/sample/cutoffs_full.json          — single consolidated JSON dump
    data/sample/schema_doc.json            — schema + summary stats

Run: python -m etl.export_samples
"""
import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

DB_PATH = "db/neet.db"
OUT_DIR = "data/sample"


def fetch_colleges(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM colleges ORDER BY state, name")
    return [dict(r) for r in cur.fetchall()]


def fetch_cutoffs(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            cu.year, cu.round, cu.quota,
            co.name AS college_name, co.state AS college_state, co.type AS college_type,
            cr.name AS course, cu.category, cu.gender, cu.pwd_flag,
            cu.domicile_state, cu.seat_type,
            cu.opening_rank, cu.closing_rank,
            cu.opening_score, cu.closing_score,
            cu.source_file
        FROM cutoffs cu
        JOIN colleges co ON co.id = cu.college_id
        JOIN courses cr ON cr.id = cu.course_id
        ORDER BY cu.year DESC, cu.quota, cu.round, co.state, co.name, cu.category
    """)
    return [dict(r) for r in cur.fetchall()]


def write_colleges_csv(colleges, out_dir: Path):
    path = out_dir / "colleges.csv"
    with path.open("w", newline="") as f:
        if not colleges:
            return
        writer = csv.DictWriter(f, fieldnames=colleges[0].keys())
        writer.writeheader()
        writer.writerows(colleges)
    print(f"  → {path} ({len(colleges)} rows)")


def write_split_csvs(cutoffs, out_dir: Path):
    """One CSV per (quota, year)."""
    grouped = defaultdict(list)
    for r in cutoffs:
        grouped[(r["quota"], r["year"])].append(r)

    for (quota, year), rows in sorted(grouped.items()):
        path = out_dir / f"cutoffs_{quota}_{year}.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"  → {path} ({len(rows)} rows)")


def write_full_json(cutoffs, colleges, out_dir: Path):
    path = out_dir / "cutoffs_full.json"
    payload = {
        "schema_version": "1.0",
        "colleges_count": len(colleges),
        "cutoffs_count": len(cutoffs),
        "colleges": colleges,
        "cutoffs": cutoffs,
    }
    path.write_text(json.dumps(payload, indent=2))
    print(f"  → {path} ({len(cutoffs)} cutoff rows)")


def write_schema_doc(conn, out_dir: Path):
    """Document the schema + descriptive statistics."""
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM colleges")
    college_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM cutoffs")
    cutoff_count = cur.fetchone()["c"]

    cur.execute("SELECT DISTINCT state FROM colleges ORDER BY state")
    states = [r["state"] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT year FROM cutoffs ORDER BY year")
    years = [r["year"] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT category FROM cutoffs ORDER BY category")
    categories = [r["category"] for r in cur.fetchall()]

    cur.execute("SELECT quota, COUNT(*) AS c FROM cutoffs GROUP BY quota")
    by_quota = {r["quota"]: r["c"] for r in cur.fetchall()}

    schema_doc = {
        "tables": {
            "colleges": ["id", "name", "state", "type", "established_year", "is_women_only"],
            "courses": ["id", "name"],
            "cutoffs": [
                "id", "year", "round", "quota", "college_id", "course_id",
                "category", "gender", "pwd_flag", "domicile_state", "seat_type",
                "opening_rank", "closing_rank", "opening_score", "closing_score",
                "source_file", "created_at",
            ],
        },
        "summary": {
            "colleges_total": college_count,
            "cutoffs_total": cutoff_count,
            "states_covered": states,
            "years_covered": years,
            "categories_covered": categories,
            "rows_by_quota": by_quota,
        },
    }
    path = out_dir / "schema_doc.json"
    path.write_text(json.dumps(schema_doc, indent=2))
    print(f"  → {path}")


def main():
    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        print("Exporting sample data...")
        colleges = fetch_colleges(conn)
        cutoffs = fetch_cutoffs(conn)

        write_colleges_csv(colleges, out_dir)
        write_split_csvs(cutoffs, out_dir)
        write_full_json(cutoffs, colleges, out_dir)
        write_schema_doc(conn, out_dir)
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
