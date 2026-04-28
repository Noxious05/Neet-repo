# Architecture

NEET Counseling Recommendation Engine — design overview, algorithm, and edge-case handling.

## 1. Database Design

**Engine**: SQLite (file-based, zero-setup, ships in repo). Schema portable to PostgreSQL — only the `INTEGER PRIMARY KEY AUTOINCREMENT` syntax differs.

**Tables**

- `colleges (id, name, state, type, established_year, is_women_only)` — institution master. `type ∈ {AIIMS, AFMC, CENTRAL, GOVT, DEEMED, PRIVATE}` for tier-based ranking.
- `courses (id, name)` — MBBS, BDS.
- `cutoffs (id, year, round, quota, college_id, course_id, category, gender, pwd_flag, domicile_state, seat_type, opening_rank, closing_rank, opening_score, closing_score, source_file)` — the fact table. One row per (college, course, year, round, quota, category, gender) cutoff observation.

##

The recommendation path is "given user category + quota + course, find all eligible cutoffs." The composite index `(category, quota, year, round, closing_rank)` makes that an index-only scan on SQLite. `domicile_state` is denormalized onto the cutoff row (rather than derived from `colleges.state`) because state-quota seats can in principle be tagged for a domicile that differs from the college's state in special arrangements — keeping the column makes the engine tolerate that without re-querying.

##

**View `v_latest_cutoffs`** materializes the most recent cutoff per (college, course, category, quota, gender, domicile) bucket — used for fast "show me this college's latest closing rank" lookups in explanations.

NRI / Management / Institutional seats. These follow non-merit selection logic and should never enter merit-based predictions; filtering at load time keeps the engine safe by construction.

## 2. Recommendation Algorithm

**Pipeline:** eligibility filter → recency-weighted margin → bucket classification → tier-aware Top-N selection.

### 2.1 Eligibility Filter
Single SQL query selects all cutoff rows the user can compete for:
- `quota = 'AIQ'` always included
- `quota = 'STATE'` only where `colleges.state = user.domicile_state`
- `category ∈ {user.category, 'UR'}` — user can compete on own category + open seats
- `gender ∈ {'ANY', user.gender}`
- Women-only colleges excluded for male users
- PwD seats included only when `user.pwd = True`

### 2.2 Margin Score
For each eligible cutoff row:
```
raw_margin = (closing_rank - user_rank) / closing_rank
```
Positive = user better than cutoff (safer). Aggregated per (college, course, quota, category) bucket using a recency-weighted average:

```
year_weights  = {2024: 0.50, 2023: 0.30, 2022: 0.15, 2021: 0.05}
round_weights = {1: 1.00,    2: 0.70,    3: 0.40,    4: 0.20}

weight        = year_weight × round_weight
weighted_margin = Σ(weight × raw_margin) / Σ(weight)
```

Rationale: 2024 is the freshest signal; Round 1 is the cleanest signal (later rounds have noisy closing ranks driven by upgradation churn).

### 2.3 Bucket Classification
| Bucket | Weighted margin |
|---|---|
| **SAFE** | ≥ 0.15 |
| **VERY_HIGH** | 0.05 to 0.15 |
| MODERATE | -0.05 to 0.05 |
| REACH | < -0.05 |

Only **SAFE** and **VERY_HIGH** are returned per the brief.

### 2.4 Top-N Selection
Sort key (lexicographic, ascending):

1. Bucket priority — SAFE before VERY_HIGH
2. College tier — AIIMS < AFMC < CENTRAL < GOVT < DEEMED < PRIVATE
3. Prestige proxy — `latest_closing_rank` ASC (more competitive ranked higher within tier)
4. Tie-break — higher weighted margin
5. Final — more years of data

Deduplicate by `(college_id, course_name)` — pick the best quota/category combination per college so the same college isn't repeated.

`MIN_YEARS_FOR_INCLUSION = 2` excludes new colleges with thin history from Top-10 (they are still scored and visible in metadata).

### 2.5 Trend Detection
Linear regression on Round-1 (year, closing_rank) points. Reports drift % per year and labels: `stable`, `competitive`, `easing`, `sharp_competitive`, `sharp_easing`, `insufficient`. Surfaced in the response so the user can see if a college is getting harder year-over-year.

### 2.6 Explainability Payload
Each recommendation returns: `latest_closing_rank`, `latest_year`, `latest_round`, `weighted_margin`, `years_available`, `n_data_points`, `trend`, plus a human-readable `explanation` string. Confidence = `min(1, years_available/4) × trend_factor`.

## 3. Edge-Case Handling

| Case | Handling |

| **AIQ vs State Quota** | AIQ rows have no domicile filter; STATE rows require `college.state == user.domicile_state`. Single SQL `OR` clause. |

| **TN govt colleges have 0% AIQ** | TN reserves 100% of state-govt seats for state quota. AIQ rows for `(state=TN, type=GOVT)` are weight-penalized 95% in scoring so they don't crowd the Top-10 even though they exist in source data. |

| **Category fallback to UR** | OBC/SC/ST/EWS users compete on own category seats AND on UR seats. Implemented as `category IN (user_cat, 'UR')`. |

| **Women-only colleges** | `is_women_only` flag on `colleges`. Filtered with `IN (0,1)` for FEMALE users; `IN (0)` for MALE. |

| **PwD horizontal reservation** | `pwd_flag` column on cutoffs. PwD users see PwD seats only when `pwd=true`; non-PwD users never see them. |

| **NRI/Management seats** | Filtered out at ETL load time — they never enter `cutoffs`. |

| **Round drift** | Round 1 weighted highest (1.0); mop-up (round 4) weighted 0.20. Trend uses Round-1 only for stable signal. |

| **New colleges with thin history** | `MIN_YEARS_FOR_INCLUSION = 2`. Buckets with only one year of data are excluded from Top-10. |

| **Score-only states** | Schema carries both `closing_rank` and `closing_score`. Engine uses rank; score-to-rank conversion is the parser's responsibility. |

| **EWS pre-2019 absence** | Out of scope for 2021–2024 window — EWS is valid throughout. |

| **Empty result set** | Returned as empty `recommendations` list with metadata note. |

## 4. API Contract

`POST /recommend` — single endpoint. Request validates state, category, gender, rank via Pydantic. Response includes Top-10 + per-recommendation evidence + explanation + query timing. Full OpenAPI schema at `/docs`.

## 5. Performance

Median query latency on the curated dataset (2,240 rows): **~3-5 ms** end-to-end (eligibility SQL + scoring + Top-N). we can scale it upto ~100k rows on the same indexes without a query plan change. SQLite is shared as a single read-only connection across requests.

## 6. Extending to New States

Each new state is a parser plugin under `etl/parsers/<state>.py` implementing:

```python
def parse(source_path, year, round_num) -> list[dict]
```

returning rows that match the curated CSV schema. The loader (`etl/load.py`) is parser-agnostic — drop in a new parser, register it, re-load.

## 7. Future Scope — ML-Driven Data Ingestion & Scaling

To scale from a few colleges to nationwide coverage, the ingestion pipeline can evolve into an `ML-assisted, self-improving system`.
    Key Enhancements

##    1. Intelligent Parsing (Unstructured Data)
        Use layout-aware models (LayoutLM, OCR + table detection) to extract data from PDFs/HTML using Unstructured.io,DI,Liteparser.
        Apply models to identify fields like college, quota, rank, category.

##    2. Smart Standardization (Canonicalization)
        Replace manual mappings with ML:
            Text classification + embeddings to normalize labels (e.g., "GEN" → "UR")
            Use clustering to auto-handle unseen variations.

##    3. Duplicate Detection
        Identify duplicate records across sources using:
            Embedding similarity + fuzzy matching

##    4. Missing Data Handling
        Predict missing cutoffs using:
            Regression models (XGBoost)
            Time-series forecasting (ARIMA/Prophet)

##    6. Human-in-the-Loop (Active Learning)
        Only low-confidence records are flagged for manual validation
        Feedback loop improves models over time

##    7. Auto Source Discovery
        Crawl counseling websites and detect new data releases
        Classify relevant documents automatically

##    8. Adaptive Schema Evolution
        Detect new categories/seat types using clustering & anomaly detection