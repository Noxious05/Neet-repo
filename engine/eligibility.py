"""
Eligibility filter.

Given a user profile, fetches all (college, year, round, quota, category)
cutoff records the user is *eligible* to compete for. This is the
candidate pool — scoring/ranking happens downstream.

Rules implemented
-----------------
1. AIQ (15%): always eligible regardless of domicile.
2. State Quota (85%): eligible ONLY if user.domicile == college.state.
   - Tamil Nadu special case: state govt colleges are 100% state quota.
     AIQ rows for TN GOVT colleges are flagged as low-priority since
     those seats don't actually exist in practice.
3. Category: user can compete on their own category seats AND on UR seats.
   (Cannot compete on a category lower in priority than their own.)
4. Gender: ANY-gender seats + matching gender. Women-only colleges
   excluded for male users.
5. PwD: if user has PwD, include PwD seats; otherwise exclude them.
"""
from typing import TypedDict


# ============================================================
# CONFIG
# ============================================================
TN_AIQ_DEPRIORITIZE = True   # TN govt colleges have no real AIQ seats
EXCLUDED_TN_AIQ_TYPES = {"GOVT"}


# ============================================================
# TYPES
# ============================================================
class UserProfile(TypedDict):
    neet_rank: int
    category: str          # UR/OBC/SC/ST/EWS
    domicile_state: str    # 2-letter state code
    gender: str            # MALE/FEMALE
    pwd: bool
    course: str            # MBBS/BDS


def get_eligible_categories(user_category: str) -> list[str]:
    """User can compete on their own category + UR (open) seats."""
    if user_category == "UR":
        return ["UR"]
    return [user_category, "UR"]


def get_eligible_genders(user_gender: str) -> list[str]:
    """ANY-gender seats + matching gender."""
    return ["ANY", user_gender]


def build_eligibility_query(user: UserProfile) -> tuple[str, list]:
    """
    Build SQL that returns all cutoff rows the user is eligible to compete for.

    Returns:
        (sql_string, params_list)
    """
    eligible_cats = get_eligible_categories(user["category"])
    eligible_genders = get_eligible_genders(user["gender"])

    cat_placeholders = ",".join("?" for _ in eligible_cats)
    gender_placeholders = ",".join("?" for _ in eligible_genders)

    sql = f"""
        SELECT
            cu.id              AS cutoff_id,
            cu.year, cu.round, cu.quota,
            cu.category, cu.gender, cu.pwd_flag,
            cu.domicile_state,
            cu.opening_rank, cu.closing_rank,
            co.id              AS college_id,
            co.name            AS college_name,
            co.state           AS college_state,
            co.type            AS college_type,
            co.is_women_only,
            cr.name            AS course_name
        FROM cutoffs cu
        JOIN colleges co ON co.id = cu.college_id
        JOIN courses  cr ON cr.id = cu.course_id
        WHERE cr.name = ?
          AND cu.category IN ({cat_placeholders})
          AND cu.gender   IN ({gender_placeholders})
          AND (
                -- AIQ: always eligible (filter TN-govt-AIQ separately)
                cu.quota = 'AIQ'
                OR
                -- State Quota: domicile match required
                (cu.quota = 'STATE' AND co.state = ?)
              )
          AND cu.pwd_flag = ?
          AND co.is_women_only IN ({_women_only_filter(user["gender"])})
    """

    params: list = [user["course"]]
    params.extend(eligible_cats)
    params.extend(eligible_genders)
    params.append(user["domicile_state"])
    params.append(1 if user["pwd"] else 0)

    return sql, params


def _women_only_filter(gender: str) -> str:
    """Female users can apply to women-only AND co-ed colleges; males only co-ed."""
    return "0,1" if gender == "FEMALE" else "0"


def is_tn_govt_aiq_low_priority(quota: str, college_state: str, college_type: str) -> bool:
    """
    TN govt colleges effectively have no AIQ seats since TN has 100%
    state reservation for its govt colleges. Flag these rows so the
    scorer can deprioritize them.
    """
    if not TN_AIQ_DEPRIORITIZE:
        return False
    return (
        quota == "AIQ"
        and college_state == "TN"
        and college_type in EXCLUDED_TN_AIQ_TYPES
    )
