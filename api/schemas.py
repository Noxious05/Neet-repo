"""
Pydantic models for the /recommend endpoint.
We can Add More validations on Fields for Securing it from SQL-Injection
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================
# CONFIG
# ============================================================
SUPPORTED_STATES = {"TN", "KA", "MH", "UP", "MP", "DL"}
SUPPORTED_CATEGORIES = {"UR", "OBC", "SC", "ST", "EWS"}
SUPPORTED_GENDERS = {"MALE", "FEMALE"}
SUPPORTED_COURSES = {"MBBS", "BDS"}
# ============================================================


class RecommendRequest(BaseModel):
    neet_rank: int = Field(..., gt=0, le=2_500_000, description="All India NEET rank")
    category: Literal["UR", "OBC", "SC", "ST", "EWS"]
    domicile_state: str = Field(..., min_length=2, max_length=2)
    gender: Literal["MALE", "FEMALE"]
    pwd: bool = False
    course: Literal["MBBS", "BDS"] = "MBBS"

    @field_validator("domicile_state")
    @classmethod
    def _upper_state(cls, v: str) -> str:
        v = v.upper()
        if v not in SUPPORTED_STATES:
            raise ValueError(f"domicile_state must be one of {sorted(SUPPORTED_STATES)}")
        return v


class TrendInfo(BaseModel):
    label: str
    drift_pct_per_year: Optional[float] = None
    n_years: int


class Evidence(BaseModel):
    user_rank: int
    latest_closing_rank: int
    latest_year: int
    latest_round: int
    weighted_margin: float
    years_available: list[int]
    n_data_points: int
    trend: TrendInfo


class Recommendation(BaseModel):
    rank: int
    college_id: int
    college_name: str
    college_state: str
    college_type: str
    course: str
    quota: str
    category_applied: str
    safety_bucket: Literal["SAFE", "VERY_HIGH"]
    confidence: float
    evidence: Evidence


class Metadata(BaseModel):
    total_eligible_rows: int
    scored_buckets: int
    top_n_returned: int
    query_time_ms: float


class RecommendResponse(BaseModel):
    user_profile: RecommendRequest
    recommendations: list[Recommendation]
    metadata: Metadata
