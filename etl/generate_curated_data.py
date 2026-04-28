"""
Curated cutoff data generator.

Generates realistic NEET MBBS closing ranks for 30 colleges across
4 years (2021-2024), 2 rounds, AIQ + State quotas, 5 categories.

Anchored on publicly known closing-rank ballparks for top govt colleges
in MCC AIQ Round 1 and respective state DME publications. Rounded and
adjusted with deterministic year/round drift to produce a clean,
internally consistent test corpus.

Output: data/raw/curated_cutoffs.csv
"""
import csv
import random
from pathlib import Path

OUTPUT_PATH = "data/raw/curated_cutoffs.csv"
SEED = 42
YEARS = [2021, 2022, 2023, 2024]
ROUNDS = [1, 2]
CATEGORIES = ["UR", "EWS", "OBC", "SC", "ST"]

# Category multipliers applied to UR baseline closing rank
CATEGORY_MULTIPLIERS = {
    "UR":  1.00,
    "EWS": 1.12,
    "OBC": 1.45,
    "SC":  4.20,
    "ST":  8.00,
}

# Round-2 closing rank drift (later rounds typically have higher closing ranks)
ROUND_DRIFT = {1: 1.00, 2: 1.18}

# Year-over-year drift (small, college-specific noise applied per run)
YEAR_DRIFT_RANGE = (-0.08, 0.10)

# UR baseline closing ranks per (college_name, quota)
# Quota: 'AIQ' = All India Quota seats (open to all), 'STATE' = State Quota (domicile-locked)
# Numbers calibrated against publicly reported MCC/state cutoff ballparks.
COLLEGE_BASELINES = {
    # College Name : { 'AIQ': baseline_UR_round1_rank, 'STATE': baseline_UR_round1_rank }
    "AIIMS New Delhi":                                 {"AIQ": 55,    "STATE": None},
    "Maulana Azad Medical College":                    {"AIQ": 130,   "STATE": 200},
    "Lady Hardinge Medical College":                   {"AIQ": 650,   "STATE": 950},
    "Vardhman Mahavir Medical College":                {"AIQ": 320,   "STATE": 500},
    "AFMC Pune":                                       {"AIQ": 720,   "STATE": None},
    "Madras Medical College":                          {"AIQ": 1800,  "STATE": 6500},
    "Stanley Medical College":                         {"AIQ": 3500,  "STATE": 9000},
    "Government Kilpauk Medical College":              {"AIQ": 4200,  "STATE": 11500},
    "Coimbatore Medical College":                      {"AIQ": 5800,  "STATE": 14000},
    "Tirunelveli Medical College":                     {"AIQ": 8500,  "STATE": 19000},
    "Bangalore Medical College":                       {"AIQ": 1700,  "STATE": 6800},
    "Mysore Medical College":                          {"AIQ": 4500,  "STATE": 12500},
    "Karnataka Institute of Medical Sciences Hubli":   {"AIQ": 6800,  "STATE": 16000},
    "Kasturba Medical College Manipal":                {"AIQ": 12000, "STATE": None},
    "JSS Medical College Mysore":                      {"AIQ": 18500, "STATE": None},
    "Grant Medical College Mumbai":                    {"AIQ": 2200,  "STATE": 7500},
    "BJ Medical College Pune":                         {"AIQ": 3000,  "STATE": 8800},
    "Topiwala National Medical College":               {"AIQ": 4800,  "STATE": 12000},
    "Government Medical College Nagpur":               {"AIQ": 6500,  "STATE": 15500},
    "Lokmanya Tilak Medical College":                  {"AIQ": 5500,  "STATE": 13800},
    "King George Medical University":                  {"AIQ": 3800,  "STATE": 7200},
    "Ganesh Shankar Vidyarthi Memorial Medical College":{"AIQ": 7500, "STATE": 14500},
    "Motilal Nehru Medical College Allahabad":         {"AIQ": 8200,  "STATE": 15800},
    "BRD Medical College Gorakhpur":                   {"AIQ": 9500,  "STATE": 17500},
    "Sarojini Naidu Medical College Agra":             {"AIQ": 8800,  "STATE": 16500},
    "Gandhi Medical College Bhopal":                   {"AIQ": 6500,  "STATE": 9500},
    "Netaji Subhash Chandra Bose Medical College Jabalpur":{"AIQ": 9000,"STATE": 13500},
    "Mahatma Gandhi Memorial Medical College Indore":  {"AIQ": 7200,  "STATE": 10500},
    "Shyam Shah Medical College Rewa":                 {"AIQ": 11500, "STATE": 17000},
    "Gajra Raja Medical College Gwalior":              {"AIQ": 8500,  "STATE": 12500},
}

# Map college to its home state (for state quota domicile)
COLLEGE_STATE = {
    "AIIMS New Delhi": "DL",
    "Maulana Azad Medical College": "DL",
    "Lady Hardinge Medical College": "DL",
    "Vardhman Mahavir Medical College": "DL",
    "AFMC Pune": "MH",
    "Madras Medical College": "TN",
    "Stanley Medical College": "TN",
    "Government Kilpauk Medical College": "TN",
    "Coimbatore Medical College": "TN",
    "Tirunelveli Medical College": "TN",
    "Bangalore Medical College": "KA",
    "Mysore Medical College": "KA",
    "Karnataka Institute of Medical Sciences Hubli": "KA",
    "Kasturba Medical College Manipal": "KA",
    "JSS Medical College Mysore": "KA",
    "Grant Medical College Mumbai": "MH",
    "BJ Medical College Pune": "MH",
    "Topiwala National Medical College": "MH",
    "Government Medical College Nagpur": "MH",
    "Lokmanya Tilak Medical College": "MH",
    "King George Medical University": "UP",
    "Ganesh Shankar Vidyarthi Memorial Medical College": "UP",
    "Motilal Nehru Medical College Allahabad": "UP",
    "BRD Medical College Gorakhpur": "UP",
    "Sarojini Naidu Medical College Agra": "UP",
    "Gandhi Medical College Bhopal": "MP",
    "Netaji Subhash Chandra Bose Medical College Jabalpur": "MP",
    "Mahatma Gandhi Memorial Medical College Indore": "MP",
    "Shyam Shah Medical College Rewa": "MP",
    "Gajra Raja Medical College Gwalior": "MP",
}


def generate_rows():
    rng = random.Random(SEED)
    rows = []

    for college_name, baselines in COLLEGE_BASELINES.items():
        home_state = COLLEGE_STATE[college_name]

        for quota, baseline_ur in baselines.items():
            if baseline_ur is None:
                continue

            # Per-college, per-quota year drift (deterministic via seeded rng)
            yearly_drift = {
                year: 1.0 + rng.uniform(*YEAR_DRIFT_RANGE)
                for year in YEARS
            }

            for year in YEARS:
                for round_num in ROUNDS:
                    for category in CATEGORIES:
                        cat_mult = CATEGORY_MULTIPLIERS[category]
                        round_mult = ROUND_DRIFT[round_num]

                        closing_rank = int(
                            baseline_ur
                            * cat_mult
                            * round_mult
                            * yearly_drift[year]
                        )
                        # Opening rank = 60-85% of closing rank
                        opening_rank = int(closing_rank * rng.uniform(0.6, 0.85))

                        domicile = home_state if quota == "STATE" else None

                        rows.append({
                            "year": year,
                            "round": round_num,
                            "quota": quota,
                            "college_name": college_name,
                            "college_state": home_state,
                            "course": "MBBS",
                            "category": category,
                            "gender": "ANY",
                            "pwd_flag": 0,
                            "domicile_state": domicile if domicile else "",
                            "seat_type": "AIQ" if quota == "AIQ" else "SQ",
                            "opening_rank": opening_rank,
                            "closing_rank": closing_rank,
                            "opening_score": "",
                            "closing_score": "",
                            "source_file": "curated_v1",
                        })
    return rows


def main():
    rows = generate_rows()
    out_path = Path(OUTPUT_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {out_path}")
    print(f"Colleges: {len({r['college_name'] for r in rows})}")
    print(f"Years: {sorted({r['year'] for r in rows})}")
    print(f"Quotas: {sorted({r['quota'] for r in rows})}")


if __name__ == "__main__":
    main()
