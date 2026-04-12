"""
api.py — FastAPI application exposing the portfolio scoring system.

Run locally:
    pip install fastapi uvicorn
    uvicorn api:app --reload --port 8000

Holdings come from holdings.py (single source of truth — no hardcoded tickers here).

Endpoints:
    GET /api/portfolio/summary   — portfolio-level aggregation
    GET /api/positions           — all scored positions (full data)
    GET /api/positions/{ticker}  — single scored position
    GET /api/trim-candidates     — positions qualifying for trim display
    GET /api/add-candidates      — actionable add candidates (Avoid excluded)
    GET /api/review-queue        — all positions flagged for manual review

All data is generated deterministically from mock OHLCV on each request.
No database, no external API calls.
"""

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from engine import run_engine
from portfolio import (
    compute_portfolio_summary,
    TRIM_DISPLAY_THRESHOLD,
    ADD_DISPLAY_THRESHOLD,
)
from holdings import build_holdings, build_spy


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Portfolio Scoring API",
    description="Local-first portfolio decision engine. All data is deterministic mock.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Data builder — called on every request (deterministic, no caching needed)
# ---------------------------------------------------------------------------

def _build_data() -> tuple:
    """Build holdings and SPY; run engine; compute portfolio summary."""
    holdings  = build_holdings()
    spy_ohlcv = build_spy()
    results   = run_engine(holdings, spy_ohlcv)
    portfolio = compute_portfolio_summary(holdings, results)
    result_map = {r["ticker"]: r for r in results}
    return results, result_map, portfolio


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def _is_actionable_add(candidate: dict) -> bool:
    """
    Actionable = action is 'High Conviction Add' or 'Watchlist'.
    Monitor and Avoid are excluded from the /api/add-candidates endpoint.
    """
    return candidate.get("action", "").lower() in ("high conviction add", "watchlist")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/portfolio/summary", response_model=None, tags=["Portfolio"])
def get_portfolio_summary() -> Dict[str, Any]:
    """
    Portfolio-level aggregation: total value, HHI, cluster exposures,
    top positions, trim/add candidate counts, review queue count.
    """
    _, _, portfolio = _build_data()
    return {
        "summary":           portfolio["summary"],
        "cluster_exposures": portfolio["cluster_exposures"],
        "trim_candidate_count": len(portfolio["trim_candidates"]),
        "add_candidate_count":  len(
            [c for c in portfolio["add_candidates"] if _is_actionable_add(c)]
        ),
        "review_queue_count": len(portfolio["review_queue"]),
    }


@app.get("/api/positions", response_model=None, tags=["Positions"])
def get_positions() -> List[Dict[str, Any]]:
    """
    All scored positions with full per-position data (scores, components,
    explanations).
    """
    results, _, _ = _build_data()
    return results


@app.get("/api/positions/{ticker}", response_model=None, tags=["Positions"])
def get_position(ticker: str) -> Dict[str, Any]:
    """
    Single scored position by ticker symbol (case-insensitive).
    Returns 404 if the ticker is not in the portfolio.
    """
    _, result_map, _ = _build_data()
    key = ticker.upper()
    if key not in result_map:
        raise HTTPException(
            status_code=404,
            detail={
                "error":     f"Ticker '{key}' not found in portfolio.",
                "available": sorted(result_map.keys()),
            },
        )
    return result_map[key]


@app.get("/api/trim-candidates", response_model=None, tags=["Candidates"])
def get_trim_candidates() -> Dict[str, Any]:
    """
    Positions qualifying for trim display (trim_score >= threshold).
    Sorted by trim_score descending. Includes full position data.
    """
    results, result_map, portfolio = _build_data()
    candidates = []
    for c in portfolio["trim_candidates"]:
        candidates.append({
            "ticker":         c["ticker"],
            "trim_score":     c["trim_score"],
            "action":         c["action"],
            "primary_driver": c["primary_driver"],
            "risk_type":      c["risk_type"],
            "position":       result_map[c["ticker"]],
        })
    return {
        "threshold":  TRIM_DISPLAY_THRESHOLD,
        "count":      len(candidates),
        "candidates": candidates,
    }


@app.get("/api/add-candidates", response_model=None, tags=["Candidates"])
def get_add_candidates() -> Dict[str, Any]:
    """
    Actionable add candidates (add_score >= threshold AND action != 'Avoid').
    Sorted by add_score descending. Includes full position data.
    """
    results, result_map, portfolio = _build_data()
    candidates = []
    for c in portfolio["add_candidates"]:
        if not _is_actionable_add(c):
            continue
        candidates.append({
            "ticker":           c["ticker"],
            "add_score":        c["add_score"],
            "action":           c["action"],
            "opportunity_type": c["opportunity_type"],
            "primary_driver":   c["primary_driver"],
            "position":         result_map[c["ticker"]],
        })
    return {
        "threshold":  ADD_DISPLAY_THRESHOLD,
        "count":      len(candidates),
        "candidates": candidates,
    }


@app.get("/api/review-queue", response_model=None, tags=["Review"])
def get_review_queue() -> Dict[str, Any]:
    """
    All positions flagged for manual review, with flag reasons.
    Sorted by trim_score descending. Includes full position data.
    """
    results, result_map, portfolio = _build_data()
    queue = []
    for q in portfolio["review_queue"]:
        queue.append({**q, "position": result_map[q["ticker"]]})
    return {
        "count": len(queue),
        "queue": queue,
    }
