# NEET Counseling Recommendation Engine

A predictive recommendation engine that takes a NEET aspirant's rank, category, domicile, and gender, and returns the **Top 10 medical colleges** where they have a SAFE or VERY_HIGH probability of admission — with explainable evidence.

**Stack:** Python 3.11 · SQLite · FastAPI 

---

## Quickstart

### Option A: Local Python
```bash
pip install -r requirements.txt

# Build sample dataset and SQLite DB
python etl/generate_curated_data.py
python -m etl.load
python -m etl.export_samples

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

OpenAPI docs: `http://localhost:8000/docs`

---

## Sample Request

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "neet_rank": 12000,
    "category": "OBC",
    "domicile_state": "TN",
    "gender": "MALE",
    "pwd": false,
    "course": "MBBS"
  }'
```

### Response (truncated)
```json
{
  "user_profile": { "neet_rank": 12000, "category": "OBC", ... },
  "recommendations": [
    {
      "rank": 1,
      "college_name": "Coimbatore Medical College",
      "college_state": "TN",
      "college_type": "GOVT",
      "course": "MBBS",
      "quota": "STATE",
      "category_applied": "UR",
      "safety_bucket": "SAFE",
      "confidence": 1.0,
      "evidence": {
        "user_rank": 12000,
        "latest_closing_rank": 15550,
        "latest_year": 2024,
        "weighted_margin": 0.191,
        "years_available": [2021, 2022, 2023, 2024],
        "trend": { "label": "stable", "drift_pct_per_year": -1.2 }
      }
    }
  ],
  "metadata": {
    "total_eligible_rows": 544,
    "scored_buckets": 68,
    "top_n_returned": 10,
    "query_time_ms": 4.6
  }
}
```

---

## Scope

| Dimension | Coverage |
|---|---|
| Quotas | AIQ (15%) + State (85%) for TN, KA, MH, UP, MP |
| Years | 2021, 2022, 2023, 2024 |
| Rounds | Round 1, Round 2 |
| Categories | UR, OBC, SC, ST, EWS |
| Courses | MBBS (BDS supported by schema) |
| Colleges | 30 colleges across target states + Delhi premier |

The submission ships with a **curated dataset** of 2,240 cutoff rows calibrated against publicly reported MCC and state-DME ballparks. Live PDF parsers (MCC AIQ, state DMEs) are stubbed under `etl/parsers/` with documented source URLs and a clean plugin contract — see `ARCHITECTURE.md`.

---

## Project Layout

```
neet-sys/
├── data/
│   ├── raw/                       # generator output + colleges master
│   └── sample/                    # deliverable: CSV per quota/year + JSON dump
├── etl/
│   ├── generate_curated_data.py   # produces curated_cutoffs.csv (deterministic)
│   ├── normalize.py               # canonical mappings (category/gender/quota/state)
│   ├── load.py                    # CSV → SQLite
│   ├── export_samples.py          # SQLite → sample CSVs + JSON
│   └── parsers/                   # AIQ + per-state parser stubs
├── db/
│   ├── schema.sql                 # tables, indexes, view
│   └── neet.db                    # built by etl.load
├── engine/
│   ├── eligibility.py             # quota/domicile/category/gender filter
│   ├── scoring.py                 # weighted margin + bucket + Top-N
│   ├── trend.py                   # linear regression on closing-rank series
│   └── recommend.py               # orchestrator (entry point)
├── api/
│   ├── main.py                    # FastAPI app
│   └── schemas.py                 # Pydantic request/response models
├── tests/
│   ├── conftest.py                # in-memory DB fixture
│   ├── test_eligibility.py
│   ├── test_scoring.py
│   ├── test_trend.py
│   ├── test_recommend.py          # end-to-end engine tests
│   └── test_api.py                # FastAPI TestClient
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── smoke_test.py                  # stdlib-only end-to-end sanity check
├── ARCHITECTURE.md                # design + algorithm + edge cases
├── README.md
└── requirements.txt
```

---

## Running Tests

```bash
pytest tests/ -v
```

Or, without pytest:
```bash
python smoke_test.py        # exercises 6 user profiles end-to-end
```

---

## Sample Data Files

After running `python -m etl.export_samples`, the `data/sample/` folder contains:

- `colleges.csv` — 30 colleges
- `cutoffs_AIQ_<year>.csv` — AIQ cutoffs per year (4 files)
- `cutoffs_STATE_<year>.csv` — State quota cutoffs per year (4 files)
- `cutoffs_full.json` — single normalized JSON dump (schema demonstration)
- `schema_doc.json` — schema description + summary statistics
- `smoke_test_results.json` — output from 6 representative user profiles

---

## Design Rationale

See **ARCHITECTURE.md** for:
- Database schema decisions
- Scoring formula derivation
- Top-N sort priority
- Edge-case handling (TN 0% AIQ, women-only colleges, round drift, etc.)
- Performance characteristics
- How to add a new state parser
- Future Expansion using ML
