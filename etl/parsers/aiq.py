"""
AIQ (All India Quota) cutoff parser for MCC data.

Purpose:
    Parse MCC counseling result files (typically PDFs for each year/round)
    and convert them into a standardized, structured cutoff dataset used
    by the recommendation engine.

Current Status:
    This is a stub implementation. Live MCC parsing requires tools like
    `pdfplumber` or `camelot` and handling year-specific PDF layouts.
    For now, curated data is generated via `etl/generate_curated_data.py`.

Parser :
    Every data source parser must implement:
        parse(source_path: str | Path, year: int, round: int) -> list[dict]

    The parser must:
        - Read the raw source file (PDF/CSV/etc.)
        - Extract cutoff tables
        - Normalize and return rows in a consistent schema

Output Schema (per row):
    year, round, quota, college_name, college_state, course,
    category, gender, pwd_flag, domicile_state, seat_type,
    opening_rank, closing_rank, opening_score, closing_score, source_file

Design Principle:
    All parsers (AIQ, state quotas, private counseling, etc.) must follow
    this contract so new data sources can be added as plug-and-play modules
    without changing downstream systems.

Future Scope:
    - Adding support for multiple data sources beyond MCC, including:
        • State counseling authorities (state quota cutoffs)
        • Private/university counseling portals
        • Historical datasets in CSV/Excel formats
    - Implementing source-specific parser modules under `etl/parsers/`
      while maintaining the same output contract
    - Introducing automated ingestion pipelines to periodically fetch,
      parse, and update new counseling data
    - Building validation and deduplication layers to ensure data quality
      across multiple sources
    - Extend schema to support additional attributes such as fee
      structure, seat matrix, and institute ranking for richer recommendations
"""

from pathlib import Path

QUOTA = "AIQ"
SOURCE_BASE_URL = "https://mcc.nic.in"


def parse(source_path: str | Path, year: int, round_num: int) -> list[dict]:
    """
    Parse an MCC AIQ result PDF.

    Args:
        source_path: path to MCC AIQ result PDF
        year: counseling year
        round_num: round number (1, 2, 3, mop-up=4)

    Returns:
        List of canonical cutoff dicts.

    Raises:
        NotImplementedError: live parsing is not part of this submission.
    """
    raise NotImplementedError(
        "AIQ live PDF parsing is not implemented in this submission. "
        "Use etl/generate_curated_data.py for the test corpus."
    )
