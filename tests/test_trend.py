"""
Tests for trend detection.
"""
from engine.trend import detect_trend


def test_insufficient_data():
    assert detect_trend([(2024, 1000)])["label"] == "insufficient"
    assert detect_trend([])["label"] == "insufficient"


def test_stable_trend():
    pts = [(2021, 1000), (2022, 1010), (2023, 990), (2024, 1005)]
    result = detect_trend(pts)
    assert result["label"] == "stable"


def test_competitive_trend():
    """Closing rank falling = college getting more competitive."""
    pts = [(2021, 2000), (2022, 1800), (2023, 1600), (2024, 1400)]
    result = detect_trend(pts)
    assert result["label"] in ("competitive", "sharp_competitive")
    assert result["drift_pct_per_year"] < 0


def test_easing_trend():
    """Closing rank rising = college getting easier."""
    pts = [(2021, 1000), (2022, 1200), (2023, 1400), (2024, 1700)]
    result = detect_trend(pts)
    assert result["label"] in ("easing", "sharp_easing")
    assert result["drift_pct_per_year"] > 0


def test_n_years_reported():
    pts = [(2021, 1000), (2022, 1010), (2023, 990)]
    assert detect_trend(pts)["n_years"] == 3
