"""
Tests for scoring and Top-N selection.
"""
from engine.scoring import score_pool, select_top_n, _classify, SAFE_THRESHOLD


def _row(year, round_num, college_id, college_name, college_state,
         college_type, course, quota, category, closing_rank):
    return {
        "year": year, "round": round_num,
        "college_id": college_id, "college_name": college_name,
        "college_state": college_state, "college_type": college_type,
        "course_name": course, "quota": quota,
        "category": category, "gender": "ANY", "pwd_flag": 0,
        "domicile_state": None, "opening_rank": closing_rank - 200,
        "closing_rank": closing_rank,
    }


def test_classify_safe_when_user_well_below_closing():
    # margin = (10000 - 5000) / 10000 = 0.5
    assert _classify(0.5) == "SAFE"


def test_classify_very_high_when_margin_small_positive():
    assert _classify(0.08) == "VERY_HIGH"


def test_classify_moderate_around_zero():
    assert _classify(0.0) == "MODERATE"
    assert _classify(0.04) == "MODERATE"


def test_classify_reach_when_user_above_closing():
    assert _classify(-0.10) == "REACH"


def test_score_pool_safe_user():
    # User rank 500 vs college closing ~2000 → very safe
    rows = [
        _row(2024, 1, 1, "MMC", "TN", "GOVT", "MBBS", "AIQ", "UR", 2000),
        _row(2023, 1, 1, "MMC", "TN", "GOVT", "MBBS", "AIQ", "UR", 1900),
        _row(2022, 1, 1, "MMC", "TN", "GOVT", "MBBS", "AIQ", "UR", 1850),
    ]
    scored = score_pool(rows, user_rank=500)
    assert len(scored) == 1
    assert scored[0]["safety_bucket"] == "SAFE"
    assert scored[0]["weighted_margin"] >= SAFE_THRESHOLD


def test_score_pool_reach_user():
    # User rank 50000 vs closing ~2000 → reach
    rows = [
        _row(2024, 1, 1, "MMC", "TN", "GOVT", "MBBS", "AIQ", "UR", 2000),
        _row(2023, 1, 1, "MMC", "TN", "GOVT", "MBBS", "AIQ", "UR", 1900),
    ]
    scored = score_pool(rows, user_rank=50000)
    assert scored[0]["safety_bucket"] == "REACH"


def test_select_top_n_excludes_reach_and_moderate():
    rows = [
        # Safe college
        _row(2024, 1, 1, "MMC", "TN", "GOVT", "MBBS", "AIQ", "UR", 5000),
        _row(2023, 1, 1, "MMC", "TN", "GOVT", "MBBS", "AIQ", "UR", 4900),
        # Reach college
        _row(2024, 1, 2, "AIIMS", "DL", "AIIMS", "MBBS", "AIQ", "UR", 60),
        _row(2023, 1, 2, "AIIMS", "DL", "AIIMS", "MBBS", "AIQ", "UR", 58),
    ]
    scored = score_pool(rows, user_rank=1000)
    top = select_top_n(scored)
    college_names = [s["college_name"] for s in top]
    assert "MMC" in college_names
    assert "AIIMS" not in college_names  # reach


def test_top_n_orders_by_tier():
    """Govt should rank above Deemed when both are SAFE."""
    rows = [
        _row(2024, 1, 1, "Govt", "TN", "GOVT", "MBBS", "AIQ", "UR", 5000),
        _row(2023, 1, 1, "Govt", "TN", "GOVT", "MBBS", "AIQ", "UR", 4900),
        _row(2024, 1, 2, "Deemed", "KA", "DEEMED", "MBBS", "AIQ", "UR", 12000),
        _row(2023, 1, 2, "Deemed", "KA", "DEEMED", "MBBS", "AIQ", "UR", 11500),
    ]
    scored = score_pool(rows, user_rank=2000)
    top = select_top_n(scored)
    # Both safe; Govt should rank ahead of Deemed by tier
    assert top[0]["college_name"] == "Govt"
    assert top[1]["college_name"] == "Deemed"


def test_top_n_orders_by_prestige_within_tier():
    """Within the same tier, more competitive (lower closing rank) ranks higher."""
    rows = [
        # Both GOVT, both SAFE for user_rank=200
        _row(2024, 1, 1, "MAMC", "DL", "GOVT", "MBBS", "AIQ", "UR", 250),
        _row(2023, 1, 1, "MAMC", "DL", "GOVT", "MBBS", "AIQ", "UR", 245),
        _row(2024, 1, 2, "RuralCol", "MP", "GOVT", "MBBS", "AIQ", "UR", 15000),
        _row(2023, 1, 2, "RuralCol", "MP", "GOVT", "MBBS", "AIQ", "UR", 14500),
    ]
    scored = score_pool(rows, user_rank=200)
    top = select_top_n(scored)
    # MAMC (closing 250) is more prestigious than RuralCol (closing 15000)
    assert top[0]["college_name"] == "MAMC"
    assert top[1]["college_name"] == "RuralCol"


def test_min_years_required_excludes_thin_data():
    # Only 1 year of data → excluded by MIN_YEARS_FOR_INCLUSION
    rows = [
        _row(2024, 1, 1, "NewCollege", "MP", "GOVT", "MBBS", "AIQ", "UR", 10000),
    ]
    scored = score_pool(rows, user_rank=1000)
    top = select_top_n(scored)
    assert len(top) == 0
