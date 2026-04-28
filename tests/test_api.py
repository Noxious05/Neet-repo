"""
API smoke tests via FastAPI TestClient.

Requires the database to be loaded at db/neet.db. Run `python -m etl.load`
before running these tests.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def client():
    db_path = REPO_ROOT / "db" / "neet.db"
    if not db_path.exists():
        pytest.skip("db/neet.db not built — run `python -m etl.load` first")

    # Ensure CWD is the repo root so relative DB path resolves
    os.chdir(REPO_ROOT)

    from api.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_recommend_happy_path(client):
    payload = {
        "neet_rank": 10000,
        "category": "OBC",
        "domicile_state": "TN",
        "gender": "MALE",
        "pwd": False,
        "course": "MBBS",
    }
    r = client.post("/recommend", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data
    assert "metadata" in data
    assert data["user_profile"]["domicile_state"] == "TN"
    for rec in data["recommendations"]:
        assert rec["safety_bucket"] in ("SAFE", "VERY_HIGH")
        assert "explanation" in rec
        assert rec["evidence"]["user_rank"] == 10000


def test_recommend_invalid_state(client):
    payload = {
        "neet_rank": 10000,
        "category": "UR",
        "domicile_state": "ZZ",
        "gender": "MALE",
    }
    r = client.post("/recommend", json=payload)
    assert r.status_code == 422


def test_recommend_invalid_category(client):
    payload = {
        "neet_rank": 10000,
        "category": "INVALID",
        "domicile_state": "TN",
        "gender": "MALE",
    }
    r = client.post("/recommend", json=payload)
    assert r.status_code == 422


def test_recommend_negative_rank(client):
    payload = {
        "neet_rank": -1,
        "category": "UR",
        "domicile_state": "TN",
        "gender": "MALE",
    }
    r = client.post("/recommend", json=payload)
    assert r.status_code == 422


def test_recommend_top_rank_returns_premier_colleges(client):
    payload = {
        "neet_rank": 100,
        "category": "UR",
        "domicile_state": "DL",
        "gender": "MALE",
    }
    r = client.post("/recommend", json=payload)
    assert r.status_code == 200
    college_types = [rec["college_type"] for rec in r.json()["recommendations"]]
    # Should see top tier institutions
    assert any(t in ("AIIMS", "GOVT", "CENTRAL") for t in college_types)
