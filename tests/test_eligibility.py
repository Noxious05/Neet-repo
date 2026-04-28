"""
Tests for the eligibility filter.
"""
from engine.eligibility import (
    build_eligibility_query,
    get_eligible_categories,
    get_eligible_genders,
    is_tn_govt_aiq_low_priority,
)


def test_obc_user_can_compete_on_obc_and_ur():
    cats = get_eligible_categories("OBC")
    assert set(cats) == {"OBC", "UR"}


def test_ur_user_only_competes_on_ur():
    assert get_eligible_categories("UR") == ["UR"]


def test_eligible_genders_includes_any():
    assert "ANY" in get_eligible_genders("MALE")
    assert "MALE" in get_eligible_genders("MALE")


def test_male_excluded_from_women_only_colleges(db):
    user = {
        "neet_rank": 500, "category": "UR", "domicile_state": "DL",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    sql, params = build_eligibility_query(user)
    rows = db.execute(sql, params).fetchall()
    college_names = {r["college_name"] for r in rows}
    assert "Lady Hardinge Medical College" not in college_names


def test_female_can_access_women_only_colleges(db):
    user = {
        "neet_rank": 500, "category": "UR", "domicile_state": "DL",
        "gender": "FEMALE", "pwd": False, "course": "MBBS",
    }
    sql, params = build_eligibility_query(user)
    rows = db.execute(sql, params).fetchall()
    college_names = {r["college_name"] for r in rows}
    assert "Lady Hardinge Medical College" in college_names


def test_tn_domicile_user_sees_tn_state_seats(db):
    user = {
        "neet_rank": 8000, "category": "UR", "domicile_state": "TN",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    sql, params = build_eligibility_query(user)
    rows = db.execute(sql, params).fetchall()
    state_quota_rows = [r for r in rows if r["quota"] == "STATE"]
    # All state quota rows must be from TN
    assert all(r["college_state"] == "TN" for r in state_quota_rows)
    assert len(state_quota_rows) > 0


def test_non_tn_user_excluded_from_tn_state_quota(db):
    user = {
        "neet_rank": 8000, "category": "UR", "domicile_state": "KA",
        "gender": "MALE", "pwd": False, "course": "MBBS",
    }
    sql, params = build_eligibility_query(user)
    rows = db.execute(sql, params).fetchall()
    # KA user should NOT see TN State Quota rows
    tn_state_rows = [r for r in rows if r["quota"] == "STATE" and r["college_state"] == "TN"]
    assert len(tn_state_rows) == 0


def test_aiq_visible_to_all_states(db):
    """AIQ rows should be visible regardless of domicile."""
    for domicile in ("TN", "KA", "MH"):
        user = {
            "neet_rank": 5000, "category": "UR", "domicile_state": domicile,
            "gender": "MALE", "pwd": False, "course": "MBBS",
        }
        sql, params = build_eligibility_query(user)
        rows = db.execute(sql, params).fetchall()
        aiq_rows = [r for r in rows if r["quota"] == "AIQ"]
        assert len(aiq_rows) > 0


def test_tn_govt_aiq_flagged_low_priority():
    assert is_tn_govt_aiq_low_priority("AIQ", "TN", "GOVT") is True
    assert is_tn_govt_aiq_low_priority("AIQ", "KA", "GOVT") is False
    assert is_tn_govt_aiq_low_priority("STATE", "TN", "GOVT") is False
