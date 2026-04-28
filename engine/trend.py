"""
Trend detection on closing-rank time series.

Given a sequence of (yearand closing_rank) points for a single
(college, quota, category) bucket, to classify the trend.

A college whose closing rank is monotonically rising means cutoffs are
getting easier (more demand → means need to wait as easier means rank goes up because
larger rank = lower NEET score). A monotonically falling closing rank
means the college is getting more competitive.

Computing the slope via simple least-squares; convert to a percent-per-year
drift relative to the mean.

"""

# CONFIG
# ============================================================
TREND_STABLE_THRESHOLD_PCT = 5.0   # drift < 5% per year => stable
TREND_LARGE_THRESHOLD_PCT = 15.0   # drift >= 15% per year => sharp


def detect_trend(year_rank_pairs: list[tuple[int, int]]) -> dict:
    """
    Args:
        year_rank_pairs: list of (year, closing_rank), at least 2 points

    Returns:
        {
            "label": "stable" | "competitive" | "easing" | "sharp_competitive" | "sharp_easing" | "insufficient",
            "drift_pct_per_year": float | None,
            "n_years": int
        }
    """
    n = len(year_rank_pairs)
    if n < 2:
        return {"label": "insufficient", "drift_pct_per_year": None, "n_years": n}

    # Sort by year ascending
    pts = sorted(year_rank_pairs)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    if mean_y == 0:
        return {"label": "insufficient", "drift_pct_per_year": None, "n_years": n}

    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))

    slope = (num / den) if den else 0.0
    drift_pct = (slope / mean_y) * 100.0

    abs_drift = abs(drift_pct)

    if abs_drift < TREND_STABLE_THRESHOLD_PCT:
        label = "stable"
    elif drift_pct < 0:
        # Falling closing rank => more competitive over time
        label = "sharp_competitive" if abs_drift >= TREND_LARGE_THRESHOLD_PCT else "competitive"
    else:
        # Rising closing rank => easing over time
        label = "sharp_easing" if abs_drift >= TREND_LARGE_THRESHOLD_PCT else "easing"

    return {
        "label": label,
        "drift_pct_per_year": round(drift_pct, 2),
        "n_years": n,
    }
