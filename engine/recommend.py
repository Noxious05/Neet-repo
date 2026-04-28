"""
Recommendation orchestrator.

Public entry point:
    recommend(conn, user_profile) -> dict

Pipeline:
    1. Build eligibility SQL from user profile
    2. Execute against SQLite
    3. Score the eligible pool
    4. Select Top 10
    5. Attach explainability metadata
"""
import sqlite3
import time

from .eligibility import build_eligibility_query, UserProfile
from .scoring import score_pool, select_top_n, build_explanation

# ============================================================
TOP_N = 10
# ============================================================


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def recommend(conn: sqlite3.Connection, user: UserProfile) -> dict:
    """
    Run the recommendation pipeline for one user.

    Args:
        conn: open SQLite connection (must have row_factory=sqlite3.Row)
        user: UserProfile dict

    Returns:
        Response dict matching the API contract.
    """
    t0 = time.perf_counter()

    sql, params = build_eligibility_query(user)
    cur = conn.cursor()
    cur.execute(sql, params)
    eligible_rows = [_row_to_dict(r) for r in cur.fetchall()]
    

    scored = score_pool(eligible_rows, user["neet_rank"])
    top = select_top_n(scored, top_n=TOP_N)

    recommendations = []
    for i, s in enumerate(top, start=1):
        confidence = round(min(1.0, len(s["years_available"]) / 4 * (1.0 if s["trend"]["label"] != "insufficient" else 0.7)), 2)
        recommendations.append({
            "rank": i,
            "college_id": s["college_id"],
            "college_name": s["college_name"],
            "college_state": s["college_state"],
            "college_type": s["college_type"],
            "course": s["course_name"],
            "quota": s["quota"],
            "category_applied": s["category_applied"],
            "safety_bucket": s["safety_bucket"],
            "confidence": confidence,
            "evidence": {
                "user_rank": user["neet_rank"],
                "latest_closing_rank": s["latest_closing_rank"],
                "latest_year": s["latest_year"],
                "latest_round": s["latest_round"],
                "weighted_margin": s["weighted_margin"],
                "years_available": s["years_available"],
                "n_data_points": s["n_data_points"],
                "trend": s["trend"],
            },
        })

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "user_profile": user,
        "recommendations": recommendations,
        "metadata": {
            "total_eligible_rows": len(eligible_rows),
            "scored_buckets": len(scored),
            "top_n_returned": len(recommendations),
            "query_time_ms": elapsed_ms,
        },
    }
