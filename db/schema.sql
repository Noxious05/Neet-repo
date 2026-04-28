-- NEET Counseling Recommendation Engine - Database Schema
-- Designed for SQLite; portable to PostgreSQL with minimal changes.

PRAGMA foreign_keys = ON;

-- ============================================================
-- MASTER TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS colleges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    state           TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN ('GOVT', 'CENTRAL', 'DEEMED', 'PRIVATE', 'AIIMS', 'AFMC')),
    established_year INTEGER,
    is_women_only   INTEGER NOT NULL DEFAULT 0,  -- 0=False, 1=True
    UNIQUE (name, state)
);

CREATE TABLE IF NOT EXISTS courses (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE             -- MBBS, BDS
);

-- ============================================================
-- FACT TABLE - cutoffs
-- ============================================================
-- Each row = one closing rank/score for a (college, course, year, round,
-- quota, category, gender, pwd, domicile) combination.

CREATE TABLE IF NOT EXISTS cutoffs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    year            INTEGER NOT NULL,
    round           INTEGER NOT NULL,                            -- 1, 2, 3, 4 (mop-up)
    quota           TEXT NOT NULL CHECK (quota IN ('AIQ', 'STATE')),
    college_id      INTEGER NOT NULL REFERENCES colleges(id),
    course_id       INTEGER NOT NULL REFERENCES courses(id),
    category        TEXT NOT NULL CHECK (category IN ('UR', 'OBC', 'SC', 'ST', 'EWS')),
    gender          TEXT NOT NULL DEFAULT 'ANY' CHECK (gender IN ('ANY', 'MALE', 'FEMALE')),
    pwd_flag        INTEGER NOT NULL DEFAULT 0,                   -- 0=False, 1=True
    domicile_state  TEXT,                                         -- NULL for AIQ
    seat_type       TEXT NOT NULL DEFAULT 'OPEN'
                     CHECK (seat_type IN ('OPEN', 'SQ', 'AIQ', 'CENTRAL')),
    opening_rank    INTEGER,
    closing_rank    INTEGER,
    opening_score   INTEGER,
    closing_score   INTEGER,
    source_file     TEXT,                                         -- audit trail
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES - tuned for the recommendation hot path
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_cutoffs_lookup
    ON cutoffs (category, quota, year, round, closing_rank);

CREATE INDEX IF NOT EXISTS idx_cutoffs_college
    ON cutoffs (college_id, year, round);

CREATE INDEX IF NOT EXISTS idx_cutoffs_domicile
    ON cutoffs (domicile_state, quota);

CREATE INDEX IF NOT EXISTS idx_colleges_state
    ON colleges (state, type);

-- ============================================================
-- VIEW - latest closing rank per college/category/quota
-- Used as a fast lookup for the engine.
-- ============================================================

CREATE VIEW IF NOT EXISTS v_latest_cutoffs AS
SELECT
    c.college_id,
    c.course_id,
    c.category,
    c.quota,
    c.gender,
    c.domicile_state,
    c.year,
    c.round,
    c.closing_rank,
    c.opening_rank
FROM cutoffs c
INNER JOIN (
    SELECT college_id, course_id, category, quota, gender,
           COALESCE(domicile_state, '') AS dom_key,
           MAX(year * 10 + round) AS latest_key
    FROM cutoffs
    GROUP BY college_id, course_id, category, quota, gender, COALESCE(domicile_state, '')
) latest
  ON c.college_id = latest.college_id
 AND c.course_id  = latest.course_id
 AND c.category   = latest.category
 AND c.quota      = latest.quota
 AND c.gender     = latest.gender
 AND COALESCE(c.domicile_state, '') = latest.dom_key
 AND (c.year * 10 + c.round) = latest.latest_key;
