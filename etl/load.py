"""
ETL Loader: reads curated CSVs from data/raw/ and populates the
SQLite database defined in db/schema.sql.

Run: python -m etl.load
"""
import csv
import sqlite3
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
DB_PATH = "db/neet.db"
SCHEMA_PATH = "db/schema.sql"
COLLEGES_CSV = "data/raw/colleges.csv"
CUTOFFS_CSV = "data/raw/curated_cutoffs.csv"
COURSES_DEFAULT = ["MBBS", "BDS"]

# ============================================================


def init_db(conn: sqlite3.Connection, schema_path: str) -> None:
    """Drop any existing tables and recreate from schema."""
    schema_sql = Path(schema_path).read_text()
    cur = conn.cursor()
    # Clean slate for deterministic loads
    cur.executescript("""
        DROP VIEW IF EXISTS v_latest_cutoffs;
        DROP TABLE IF EXISTS cutoffs;
        DROP TABLE IF EXISTS courses;
        DROP TABLE IF EXISTS colleges;
    """)
    cur.executescript(schema_sql)
    conn.commit()


def load_courses(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert default courses and return name -> id map."""
    cur = conn.cursor()
    course_ids = {}
    for course_name in COURSES_DEFAULT:
        cur.execute("INSERT INTO courses (name) VALUES (?)", (course_name,))
        course_ids[course_name] = cur.lastrowid
    conn.commit()
    return course_ids


def load_colleges(conn: sqlite3.Connection, csv_path: str) -> dict[str, int]:
    """Insert colleges from CSV and return name -> id map."""
    cur = conn.cursor()
    college_ids = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cur.execute("""
                INSERT INTO colleges (name, state, type, established_year, is_women_only)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["name"].strip(),
                row["state"].strip(),
                row["type"].strip(),
                int(row["established_year"]) if row["established_year"] else None,
                int(row["is_women_only"]),
            ))
            college_ids[row["name"].strip()] = cur.lastrowid
    conn.commit()
    return college_ids


def load_cutoffs(
    conn: sqlite3.Connection,
    csv_path: str,
    college_ids: dict[str, int],
    course_ids: dict[str, int],
) -> int:
    """Insert cutoff rows. Returns count inserted."""
    cur = conn.cursor()
    inserted = 0
    skipped = 0

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            college_id = college_ids.get(row["college_name"].strip())
            course_id = course_ids.get(row["course"].strip())

            if college_id is None or course_id is None:
                skipped += 1
                continue

            domicile = row["domicile_state"].strip() or None
            opening_rank = int(row["opening_rank"]) if row["opening_rank"] else None
            closing_rank = int(row["closing_rank"]) if row["closing_rank"] else None

            cur.execute("""
                INSERT INTO cutoffs (
                    year, round, quota, college_id, course_id,
                    category, gender, pwd_flag, domicile_state, seat_type,
                    opening_rank, closing_rank, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["year"]),
                int(row["round"]),
                row["quota"].strip(),
                college_id,
                course_id,
                row["category"].strip(),
                row["gender"].strip() or "ANY",
                int(row["pwd_flag"]),
                domicile,
                row["seat_type"].strip(),
                opening_rank,
                closing_rank,
                row["source_file"].strip(),
            ))
            inserted += 1

    conn.commit()
    if skipped:
        print(f"WARN: skipped {skipped} rows (unknown college/course)")
    return inserted


def main():
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        init_db(conn, SCHEMA_PATH)
        course_ids = load_courses(conn)
        college_ids = load_colleges(conn, COLLEGES_CSV)
        cutoff_count = load_cutoffs(conn, CUTOFFS_CSV, college_ids, course_ids)

        print(f"Loaded {len(course_ids)} courses")
        print(f"Loaded {len(college_ids)} colleges")
        print(f"Loaded {cutoff_count} cutoff rows")
        print(f"Database: {db_path.resolve()}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
