"""
Pytest fixtures.

Builds an in-memory SQLite DB seeded with a small fixture dataset
covering the rules and edge cases under test.
"""
import sqlite3
from pathlib import Path

import pytest


SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


@pytest.fixture
def db():
    """Fresh in-memory DB seeded with a deterministic test dataset."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Apply schema
    schema_sql = SCHEMA_PATH.read_text()
    conn.executescript(schema_sql)

    cur = conn.cursor()

    # Courses
    cur.execute("INSERT INTO courses (id, name) VALUES (1, 'MBBS'), (2, 'BDS')")

    # Colleges (id, name, state, type, established_year, is_women_only)
    colleges = [
        (1, "Madras Medical College", "TN", "GOVT", 1835, 0),
        (2, "Bangalore Medical College", "KA", "GOVT", 1955, 0),
        (3, "Grant Medical College Mumbai", "MH", "GOVT", 1845, 0),
        (4, "Lady Hardinge Medical College", "DL", "GOVT", 1916, 1),  # women-only
        (5, "Kasturba Medical College Manipal", "KA", "DEEMED", 1953, 0),
        (6, "AIIMS New Delhi", "DL", "AIIMS", 1956, 0),
    ]
    cur.executemany(
        "INSERT INTO colleges (id, name, state, type, established_year, is_women_only) "
        "VALUES (?, ?, ?, ?, ?, ?)", colleges
    )

    # Cutoffs — small, hand-crafted to exercise every rule
    # (year, round, quota, college_id, course_id, category, gender, pwd_flag,
    #  domicile_state, seat_type, opening_rank, closing_rank)
    cutoffs = [
        # Madras Medical AIQ MBBS UR — moderate competitiveness
        (2024, 1, "AIQ", 1, 1, "UR",  "ANY", 0, None, "AIQ", 1500, 2000),
        (2023, 1, "AIQ", 1, 1, "UR",  "ANY", 0, None, "AIQ", 1400, 1900),
        (2022, 1, "AIQ", 1, 1, "UR",  "ANY", 0, None, "AIQ", 1300, 1850),
        # Madras Medical State Quota MBBS UR — open to TN domiciles only
        (2024, 1, "STATE", 1, 1, "UR",  "ANY", 0, "TN", "SQ", 5000, 7000),
        (2023, 1, "STATE", 1, 1, "UR",  "ANY", 0, "TN", "SQ", 4800, 6800),
        (2022, 1, "STATE", 1, 1, "UR",  "ANY", 0, "TN", "SQ", 4500, 6500),
        # Madras Medical State Quota MBBS OBC
        (2024, 1, "STATE", 1, 1, "OBC", "ANY", 0, "TN", "SQ", 7500, 10000),
        (2023, 1, "STATE", 1, 1, "OBC", "ANY", 0, "TN", "SQ", 7200, 9800),
        (2022, 1, "STATE", 1, 1, "OBC", "ANY", 0, "TN", "SQ", 7000, 9500),
        # Bangalore Medical AIQ UR
        (2024, 1, "AIQ", 2, 1, "UR",  "ANY", 0, None, "AIQ", 1300, 1700),
        (2023, 1, "AIQ", 2, 1, "UR",  "ANY", 0, None, "AIQ", 1250, 1650),
        (2022, 1, "AIQ", 2, 1, "UR",  "ANY", 0, None, "AIQ", 1200, 1600),
        # Grant Medical State Quota MBBS UR — MH domicile only
        (2024, 1, "STATE", 3, 1, "UR",  "ANY", 0, "MH", "SQ", 6000, 8000),
        (2023, 1, "STATE", 3, 1, "UR",  "ANY", 0, "MH", "SQ", 5800, 7800),
        (2022, 1, "STATE", 3, 1, "UR",  "ANY", 0, "MH", "SQ", 5500, 7500),
        # Lady Hardinge AIQ UR — women-only
        (2024, 1, "AIQ", 4, 1, "UR",  "ANY", 0, None, "AIQ", 400, 700),
        (2023, 1, "AIQ", 4, 1, "UR",  "ANY", 0, None, "AIQ", 380, 680),
        (2022, 1, "AIQ", 4, 1, "UR",  "ANY", 0, None, "AIQ", 360, 660),
        # KMC Manipal AIQ UR — Deemed
        (2024, 1, "AIQ", 5, 1, "UR",  "ANY", 0, None, "AIQ", 9000, 12000),
        (2023, 1, "AIQ", 5, 1, "UR",  "ANY", 0, None, "AIQ", 8800, 11500),
        (2022, 1, "AIQ", 5, 1, "UR",  "ANY", 0, None, "AIQ", 8500, 11000),
        # AIIMS Delhi AIQ UR — extremely competitive
        (2024, 1, "AIQ", 6, 1, "UR",  "ANY", 0, None, "AIQ", 30, 60),
        (2023, 1, "AIQ", 6, 1, "UR",  "ANY", 0, None, "AIQ", 28, 58),
        (2022, 1, "AIQ", 6, 1, "UR",  "ANY", 0, None, "AIQ", 25, 55),
    ]
    cur.executemany("""
        INSERT INTO cutoffs (year, round, quota, college_id, course_id,
            category, gender, pwd_flag, domicile_state, seat_type,
            opening_rank, closing_rank)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, cutoffs)

    conn.commit()
    yield conn
    conn.close()
