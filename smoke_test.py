"""
Stdlib-only smoke test of the recommendation pipeline.

Exercises eligibility + scoring + Top N selection against the
curated SQLite DB without requiring pytest or FastAPI. Useful for
local verification and CI when full deps aren't available.

Run: python smoke_test.py
"""
import sqlite3
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT))

from engine.recommend import recommend  # noqa: E402

DB_PATH = REPO_ROOT / "db" / "neet.db"


def run_case(label, conn, user):
    print(f"\n{'=' * 70}")
    print(f"CASE: {label}")
    print(f"  Profile: {user}")
    result = recommend(conn, user)
    meta = result["metadata"]
    print(f"  Eligible rows: {meta['total_eligible_rows']}, "
          f"Buckets: {meta['scored_buckets']}, "
          f"Returned: {meta['top_n_returned']}, "
          f"Time: {meta['query_time_ms']}ms")
    if result["recommendations"]:
        print(f"  Top recommendations:")
        for rec in result["recommendations"][:5]:
            print(f"    {rec['rank']:2d}. [{rec['safety_bucket']:>9}] "
                  f"{rec['college_name']:<55} ({rec['quota']:>5}/{rec['category_applied']:>3}) "
                  f"closing={rec['evidence']['latest_closing_rank']:>6} "
                  f"margin={rec['evidence']['weighted_margin']:+.3f}")
    else:
        print("  No recommendations.")
    return result


def main():
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}. Run: python -m etl.load")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cases = [
        ("Top scorer (rank 100), DL, UR Male", {
            "neet_rank": 100, "category": "UR", "domicile_state": "DL",
            "gender": "MALE", "pwd": False, "course": "MBBS",
        }),
        ("Mid-tier (rank 12000), TN, OBC Male", {
            "neet_rank": 12000, "category": "OBC", "domicile_state": "TN",
            "gender": "MALE", "pwd": False, "course": "MBBS",
        }),
        ("Mid-tier (rank 12000), KA, OBC Male", {
            "neet_rank": 12000, "category": "OBC", "domicile_state": "KA",
            "gender": "MALE", "pwd": False, "course": "MBBS",
        }),
        ("SC user (rank 25000), MH", {
            "neet_rank": 25000, "category": "SC", "domicile_state": "MH",
            "gender": "FEMALE", "pwd": False, "course": "MBBS",
        }),
        ("ST user (rank 60000), MP", {
            "neet_rank": 60000, "category": "ST", "domicile_state": "MP",
            "gender": "MALE", "pwd": False, "course": "MBBS",
        }),
        ("Low rank (rank 200000), UP, UR", {
            "neet_rank": 200000, "category": "UR", "domicile_state": "UP",
            "gender": "MALE", "pwd": False, "course": "MBBS",
        }),
    ]

    results = {}
    for label, user in cases:
        results[label] = run_case(label, conn, user)

    # Save the full output for manual inspection
    sample_out = REPO_ROOT / "data" / "sample" / "smoke_test_results.json"
    sample_out.parent.mkdir(parents=True, exist_ok=True)
    sample_out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n→ Full results saved to {sample_out}")

    conn.close()
    print("\n✓ Smoke test complete.")


if __name__ == "__main__":
    main()
