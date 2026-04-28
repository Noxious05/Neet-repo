"""
Safety scoring for the recommendation engine.

Aggregates multiple historical cutoffs for one (college, quota, category)
bucket into a single weighted margin score, then classifies into a
safety bucket.

Margin formula
--------------
For each historical row:
    raw_margin = (closing_rank - user_rank) / closing_rank

  > 0  => user rank is BETTER (lower number) than closing → safer
  = 0  => exactly at cutoff
  < 0  => user rank is worse than closing → unsafe

Weighted margin = Σ (year_w x round_w x raw_margin) / Σ (year_w x round_w)

Buckets
-------
SAFE       : weighted_margin >= SAFE_THRESHOLD
VERY_HIGH  : VERY_HIGH_THRESHOLD <= margin < SAFE_THRESHOLD
MODERATE   : -VERY_HIGH_THRESHOLD <= margin < VERY_HIGH_THRESHOLD
REACH      : margin < -VERY_HIGH_THRESHOLD

"""
from collections import defaultdict
from .trend import detect_trend
from .eligibility import is_tn_govt_aiq_low_priority


YEAR_WEIGHTS = {
    2024: 0.50,
    2023: 0.30,
    2022: 0.15,
    2021: 0.05,
}
ROUND_WEIGHTS = {
    1: 1.00,
    2: 0.70,
    3: 0.40,
    4: 0.20, 
}

SAFE_THRESHOLD = 0.15
VERY_HIGH_THRESHOLD = 0.05
MIN_YEARS_FOR_INCLUSION = 2

# College tier ordering for tie-breaking
TIER_RANK = {
    "AIIMS":   1,
    "AFMC":    2,
    "CENTRAL": 3,
    "GOVT":    4,
    "DEEMED":  5,
    "PRIVATE": 6,
}

# Penalty applied to TN govt AIQ rows (these seats don't exist)
TN_AIQ_GOVT_PENALTY = 0.95
# ============================================================


def _bucket_key(row: dict) -> tuple:
    """Group cutoff rows by (college, course, quota, category)."""
    return (
        row["college_id"],
        row["course_name"],
        row["quota"],
        row["category"],
    )


def _row_weight(row: dict) -> float:
    yw = YEAR_WEIGHTS.get(row["year"], 0.0)
    rw = ROUND_WEIGHTS.get(row["round"], 0.0)
    base = yw * rw
    if is_tn_govt_aiq_low_priority(row["quota"], row["college_state"], row["college_type"]):
        base *= (1 - TN_AIQ_GOVT_PENALTY)
    return base


def _classify(margin: float) -> str:
    if margin >= SAFE_THRESHOLD:
        return "SAFE"
    if margin >= VERY_HIGH_THRESHOLD:
        return "VERY_HIGH"
    if margin >= -VERY_HIGH_THRESHOLD:
        return "MODERATE"
    return "REACH"


def score_pool(eligible_rows: list[dict], user_rank: int) -> list[dict]:
    """
    Group eligible cutoff rows into buckets and compute a safety score per bucket.

    Args:
        eligible_rows: rows from the eligibility query
        user_rank: user's NEET All India Rank

    Returns:
        List of scored bucket dicts, one per (college, course, quota, category).
    """
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for r in eligible_rows:
        if r["closing_rank"] is None or r["closing_rank"] <= 0:
            continue
        grouped[_bucket_key(r)].append(r)

    scored = []
    for key, rows in grouped.items():
        college_id, course_name, quota, category = key

        # Recency-weighted margin
        weighted_num = 0.0
        weight_sum = 0.0
        for r in rows:
            w = _row_weight(r)
            if w == 0:
                continue
            raw_margin = (r["closing_rank"] - user_rank) / r["closing_rank"]
            weighted_num += w * raw_margin
            weight_sum += w

        if weight_sum == 0:
            continue

        weighted_margin = weighted_num / weight_sum

        # Trend on Round-1 entries across years (cleanest signal)
        round1_rows = [r for r in rows if r["round"] == 1]
        year_rank_pairs = [(r["year"], r["closing_rank"]) for r in round1_rows]
        trend = detect_trend(year_rank_pairs)

        # Latest closing rank for evidence
        latest = max(rows, key=lambda r: (r["year"], r["round"]))

        years_available = sorted({r["year"] for r in rows})

        scored.append({
            "college_id": college_id,
            "college_name": rows[0]["college_name"],
            "college_state": rows[0]["college_state"],
            "college_type": rows[0]["college_type"],
            "course_name": course_name,
            "quota": quota,
            "category_applied": category,
            "weighted_margin": round(weighted_margin, 4),
            "safety_bucket": _classify(weighted_margin),
            "latest_closing_rank": latest["closing_rank"],
            "latest_year": latest["year"],
            "latest_round": latest["round"],
            "years_available": years_available,
            "n_data_points": len(rows),
            "trend": trend,
            "is_tn_govt_aiq": is_tn_govt_aiq_low_priority(quota, rows[0]["college_state"], rows[0]["college_type"]),
        })

    return scored


def select_top_n(scored: list[dict], top_n: int = 10) -> list[dict]:
    """
    Select Top N from SAFE U VERY_HIGH buckets.

    Ranking:
        1. Bucket priority: SAFE > VERY_HIGH
        2. College tier (AIIMS > AFMC > GOVT > DEEMED > PRIVATE)
        3. Higher weighted margin (safer first)
        4. More years of data (more reliable first)

    Deduplicates by (college, course) — picks the best quota/category
    combination per college.
    """
    eligible = [
        s for s in scored
        if s["safety_bucket"] in ("SAFE", "VERY_HIGH")
        and len(s["years_available"]) >= MIN_YEARS_FOR_INCLUSION
    ]

    # Deduplicate: keep the best entry per (college_id, course_name)
    best_per_college: dict[tuple, dict] = {}
    for s in eligible:
        key = (s["college_id"], s["course_name"])
        cur = best_per_college.get(key)
        if cur is None or _sort_key(s) < _sort_key(cur):
            best_per_college[key] = s

    deduped = list(best_per_college.values())
    deduped.sort(key=_sort_key)
    return deduped[:top_n]


def _sort_key(s: dict) -> tuple:
    """
    Sort priority:
        1. Bucket: SAFE before VERY_HIGH
        2. Tier: AIIMS > AFMC > CENTRAL > GOVT > DEEMED > PRIVATE
        3. Prestige proxy: latest closing_rank ASC (more competitive = more prestigious).
        4. Tie-break: higher margin first
        5. Final tie-break: more years of data

    """
    bucket_priority = 0 if s["safety_bucket"] == "SAFE" else 1
    tier = TIER_RANK.get(s["college_type"], 99)
    return (
        bucket_priority,
        tier,
        s["latest_closing_rank"],          # ASC — prestige first
        -s["weighted_margin"],             # higher margin breaks ties
        -len(s["years_available"]),
    )


def build_explanation(s: dict, user_rank: int) -> str:
    """Human-readable explanation string."""
    margin_pct = round(s["weighted_margin"] * 100, 1)
    trend_label = s["trend"]["label"]
    parts = [
        f"Your rank {user_rank} vs. {s['latest_year']} R{s['latest_round']} "
        f"closing rank {s['latest_closing_rank']} for {s['category_applied']} "
        f"{s['quota']} → margin {margin_pct}%.",
    ]
    if trend_label not in ("insufficient", "stable"):
        drift = s["trend"]["drift_pct_per_year"]
        parts.append(
            f"Trend: {trend_label.replace('_', ' ')} ({drift:+.1f}% rank drift/year)."
        )
    elif trend_label == "stable":
        parts.append("Trend: closing rank stable across years.")
    parts.append(f"Based on {s['n_data_points']} data points across {len(s['years_available'])} years.")
    return " ".join(parts)
