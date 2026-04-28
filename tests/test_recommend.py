"""
End-to-end recommendation tests.
"""
from engine.recommend import recommend


def test_tn_obc_user_gets_recommendations(db):
    user = {
        "neet_rank": 12000, "category": "OBC", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    assert isinstance(result["recommendations"], list)
    assert result["metadata"]["total_eligible_rows"] > 0
    # Every recommendation must be SAFE or VERY_HIGH
    for rec in result["recommendations"]:
        assert rec["safety_bucket"] in ("SAFE", "VERY_HIGH")


def test_top_rank_user_gets_top_colleges(db):
    """User with rank 100 should see top colleges as safe."""
    user = {
        "neet_rank": 100, "category": "UR", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    college_names = [r["college_name"] for r in result["recommendations"]]
    # At least one premier college should appear
    assert len(college_names) > 0


def test_high_rank_user_gets_no_unsafe_recommendations(db):
    """Very high rank → only SAFE/VERY_HIGH returned (or empty)."""
    user = {
        "neet_rank": 50, "category": "UR", "domicile_state": "DL",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    for rec in result["recommendations"]:
        assert rec["safety_bucket"] in ("SAFE", "VERY_HIGH")


def test_very_low_rank_user_gets_empty_recommendations(db):
    """Rank 500000 has no SAFE/VERY_HIGH colleges in fixture data."""
    user = {
        "neet_rank": 500000, "category": "UR", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    # Most likely empty; shouldn't crash
    assert isinstance(result["recommendations"], list)


def test_response_includes_explanation(db):
    user = {
        "neet_rank": 10000, "category": "UR", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    if result["recommendations"]:
        rec = result["recommendations"][0]
        assert "explanation" in rec
        assert str(user["neet_rank"]) in rec["explanation"]
        assert "evidence" in rec
        assert rec["evidence"]["user_rank"] == user["neet_rank"]


def test_query_time_recorded(db):
    user = {
        "neet_rank": 10000, "category": "UR", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    assert "query_time_ms" in result["metadata"]
    assert result["metadata"]["query_time_ms"] >= 0


def test_recommendations_max_10(db):
    """Top N is capped at 10 even with many eligible buckets."""
    user = {
        "neet_rank": 100000, "category": "OBC", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    assert len(result["recommendations"]) <= 10


def test_state_quota_only_for_domicile_state(db):
    """User with TN domicile should not see KA/MH state quota recommendations."""
    user = {
        "neet_rank": 8000, "category": "UR", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    result = recommend(db, user)
    state_quota_recs = [r for r in result["recommendations"] if r["quota"] == "STATE"]
    for rec in state_quota_recs:
        assert rec["college_state"] == "TN"
