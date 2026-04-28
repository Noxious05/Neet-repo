"""
FastAPI application for the NEET counseling recommendation engine.

Endpoint:
    POST /recommend → Top 10 SAFE/VERY_HIGH college recommendations

Run:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import sqlite3
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .schemas import RecommendRequest, RecommendResponse
from engine.recommend import recommend

# ============================================================
# CONFIG
# ============================================================
DB_PATH = "db/neet.db"
APP_TITLE = "NEET Counseling Recommendation Engine"
APP_VERSION = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("neet-api")
# ============================================================


# ============================================================
# DATABASE HANDLING
# ============================================================
def _open_connection() -> sqlite3.Connection:
    db_file = Path(DB_PATH)

    if not db_file.exists():
        logger.error(f"Database file not found at {db_file.resolve()}")
        raise FileNotFoundError("Database not initialized. Run ETL pipeline.")

    try:
        conn = sqlite3.connect(
            db_file,
            check_same_thread=False,
            timeout=10,
        )
        conn.row_factory = sqlite3.Row
        logger.info("Database connection established.")
        return conn

    except sqlite3.Error as e:
        logger.exception("Failed to connect to SQLite DB")
        raise RuntimeError("Database connection failed") from e


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.db = _open_connection()
        yield
    finally:
        try:
            app.state.db.close()
            logger.info("Database connection closed.")
        except Exception:
            logger.warning("Error closing database connection", exc_info=True)


# ============================================================
# APP INIT
# ============================================================
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Predicts Top 10 medical colleges with high admission probability.",
    lifespan=lifespan,
)


# ============================================================
# GLOBAL EXCEPTION HANDLERS
# ============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    logger.exception(f"Database error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Database operation failed"},
    )


# ============================================================
# ROUTES
# ============================================================
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@app.post("/recommend", response_model=RecommendResponse)
def post_recommend(req: RecommendRequest):
    """
    Returns Top 10 colleges where the user has SAFE or VERY_HIGH admission probability.
    """

    # Defensive input validation (extra layer beyond Pydantic)
    if req.neet_rank <= 0:
        raise HTTPException(status_code=400, detail="Invalid NEET rank")

    user_profile: Dict[str, Any] = {
        "neet_rank": req.neet_rank,
        "category": req.category,
        "domicile_state": req.domicile_state,
        "gender": req.gender,
        "pwd": req.pwd,
        "course": req.course,
    }

    try:
        result = recommend(app.state.db, user_profile)

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except sqlite3.Error as db_err:
        logger.exception("Database error during recommendation")
        raise HTTPException(status_code=500, detail="Database error")

    except Exception as e:
        logger.exception("Unexpected error in recommendation engine")
        raise HTTPException(
            status_code=500,
            detail="Recommendation engine failed",
        )

    # Handle empty recommendations gracefully
    if not result.get("recommendations"):
        result.setdefault("metadata", {})
        result["metadata"]["note"] = (
            "No SAFE or VERY_HIGH colleges found for this profile."
        )

    return result
