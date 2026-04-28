"""
State quota parser stubs.

One module per state for the 5 states in scope: TN, KA, MH, UP, MP.
Each state DME publishes its own format (PDF / HTML / Excel) so each
parser is self-contained but shares the same `parse()` contract.

CURRENT STATUS: stubs. Live parsing is out of scope for this 1-week
submission per the architecture decision to ship curated data. The
modules exist to document the source URL and parsing notes so a future
engineer can implement them without redesigning the pipeline.

To add a new state:
    1. Create etl/parsers/<state>.py with `parse(path, year, round)`.
    2. Return list of dicts matching the curated CSV schema.
    3. Wire into etl/load.py orchestrator.
"""

STATE_SOURCES = {
    "TN": {
        "name": "Tamil Nadu",
        "authority": "TN Directorate of Medical Education (DME)",
        "url": "https://tnmedicalselection.net",
        "format": "PDF",
        "notes": "Score-based; 100% state quota for TN govt colleges (no AIQ).",
    },
    "KA": {
        "name": "Karnataka",
        "authority": "Karnataka Examinations Authority (KEA)",
        "url": "https://cetonline.karnataka.gov.in",
        "format": "PDF",
        "notes": "Round-wise allotment lists; rural quota subset.",
    },
    "MH": {
        "name": "Maharashtra",
        "authority": "State CET Cell",
        "url": "https://cetcell.mahacet.org",
        "format": "PDF",
        "notes": "Multiple categories incl. SEBC; reservation overlay complex.",
    },
    "UP": {
        "name": "Uttar Pradesh",
        "authority": "UP Directorate of Medical Education",
        "url": "https://upneet.gov.in",
        "format": "PDF",
        "notes": "Round 1, 2, 3, mop-up + stray vacancy round.",
    },
    "MP": {
        "name": "Madhya Pradesh",
        "authority": "MP DME",
        "url": "https://dme.mponline.gov.in",
        "format": "PDF",
        "notes": "MP domicile + open seats; freelance quota separate.",
    },
}


def parse_stub(state: str, *args, **kwargs):
    """Common stub for all state parsers."""
    raise NotImplementedError(
        f"Live {state} state quota parsing not implemented. "
        f"Source: {STATE_SOURCES[state]['url']}. "
        f"Use etl/generate_curated_data.py for test data."
    )


# Public per-state functions (kept as separate symbols so callers can
# import them naturally: from etl.parsers.state import parse_tn, etc.)
def parse_tn(path, year, round_num): return parse_stub("TN")
def parse_ka(path, year, round_num): return parse_stub("KA")
def parse_mh(path, year, round_num): return parse_stub("MH")
def parse_up(path, year, round_num): return parse_stub("UP")
def parse_mp(path, year, round_num): return parse_stub("MP")
