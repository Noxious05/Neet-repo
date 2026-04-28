"""
Data standardization helpers for messy counseling data.

Different data sources often use inconsistent names, spellings, or codes
for the same fields (e.g., categories, states, quotas).

These helpers ensure that all such variations are cleaned and converted
into a consistent format before storing in the database.

All ETL parsers must use these functions to maintain uniform and reliable data.

"""

# ============================================================
# CATEGORY
# ============================================================
CATEGORY_MAP = {
    "UR": "UR", "GENERAL": "UR", "GEN": "UR", "OPEN": "UR",
    "OBC": "OBC", "OBC-NCL": "OBC", "BC": "OBC", "MBC": "OBC",
    "SC": "SC", "SCHEDULED CASTE": "SC",
    "ST": "ST", "SCHEDULED TRIBE": "ST",
    "EWS": "EWS", "EWS-GEN": "EWS", "EWS-PWD": "EWS",
}

# ============================================================
# GENDER
# ============================================================
GENDER_MAP = {
    "": "ANY", "ANY": "ANY", "ALL": "ANY", "BOTH": "ANY",
    "M": "MALE", "MALE": "MALE", "BOY": "MALE",
    "F": "FEMALE", "FEMALE": "FEMALE", "GIRL": "FEMALE", "WOMEN": "FEMALE",
}

# ============================================================
# QUOTA
# ============================================================
QUOTA_MAP = {
    "AIQ": "AIQ", "ALL INDIA": "AIQ", "ALL INDIA QUOTA": "AIQ",
    "STATE": "STATE", "STATE QUOTA": "STATE", "SQ": "STATE",
}

# ============================================================
# STATE - 2-letter ISO-like codes
# ============================================================
STATE_MAP = {
    "TAMIL NADU": "TN", "TN": "TN",
    "KARNATAKA": "KA", "KA": "KA",
    "MAHARASHTRA": "MH", "MH": "MH",
    "UTTAR PRADESH": "UP", "UP": "UP",
    "MADHYA PRADESH": "MP", "MP": "MP",
    "DELHI": "DL", "NEW DELHI": "DL", "DL": "DL",
    "ANDHRA PRADESH": "AP", "AP": "AP",
    "TELANGANA": "TG", "TG": "TG",
    "KERALA": "KL", "KL": "KL",
    "WEST BENGAL": "WB", "WB": "WB",
    "RAJASTHAN": "RJ", "RJ": "RJ",
    "GUJARAT": "GJ", "GJ": "GJ",
    "PUNJAB": "PB", "PB": "PB",
    "HARYANA": "HR", "HR": "HR",
}

# ============================================================
# SEAT TYPE - filter exclusions
# ============================================================
EXCLUDED_SEAT_TYPES = {"NRI", "MGMT", "MANAGEMENT", "PAID", "INSTITUTIONAL"}


def normalize_category(value: str) -> str | None:
    """Return canonical category code or None if unrecognized."""
    if not value:
        return None
    return CATEGORY_MAP.get(value.strip().upper())


def normalize_gender(value: str) -> str:
    """Return canonical gender; defaults to ANY."""
    if value is None:
        return "ANY"
    return GENDER_MAP.get(value.strip().upper(), "ANY")


def normalize_quota(value: str) -> str | None:
    """Return canonical quota or None if unrecognized."""
    if not value:
        return None
    return QUOTA_MAP.get(value.strip().upper())


def normalize_state(value: str) -> str | None:
    """Return canonical 2-letter state code or None if unrecognized."""
    if not value:
        return None
    return STATE_MAP.get(value.strip().upper())


def is_merit_seat(seat_type: str) -> bool:
    """Reject NRI/Management/Institutional seats — different selection logic."""
    if not seat_type:
        return True
    return seat_type.strip().upper() not in EXCLUDED_SEAT_TYPES
