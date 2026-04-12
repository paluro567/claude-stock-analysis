import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from models import Holdings, EquityHolding, FullPortfolioAnalysis, PositionDetailResponse
from config import HOLDINGS_FILE, DEFAULT_HOLDINGS, CACHE_TTL
from analytics.technical import sma

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache
_cache: dict = {
    "data": None,
    "ts": 0.0,
}


def _load_holdings() -> Holdings:
    try:
        if HOLDINGS_FILE.exists():
            with open(HOLDINGS_FILE, "r") as f:
                data = json.load(f)
            return Holdings(**data)
    except Exception as e:
        logger.warning(f"Could not load holdings file: {e}, using defaults")
    return Holdings(**DEFAULT_HOLDINGS)


def _save_holdings(holdings: Holdings) -> None:
    HOLDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HOLDINGS_FILE, "w") as f:
        json.dump(holdings.model_dump(), f, indent=2)


def _invalidate_cache():
    _cache["data"] = None
    _cache["ts"] = 0.0


async def _get_analysis(force_refresh: bool = False) -> FullPortfolioAnalysis:
    """Get cached or fresh portfolio analysis."""
    from main import analyzer

    now = time.time()
    if not force_refresh and _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    holdings = _load_holdings()
    result = await analyzer.analyze(holdings)
    _cache["data"] = result
    _cache["ts"] = now
    return result


@router.get("/api/portfolio", response_model=FullPortfolioAnalysis)
async def get_portfolio():
    """Returns full portfolio analysis (cached up to 5 minutes)."""
    try:
        return await _get_analysis()
    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")


@router.get("/api/portfolio/refresh", response_model=FullPortfolioAnalysis)
async def refresh_portfolio():
    """Force refresh portfolio analysis."""
    try:
        return await _get_analysis(force_refresh=True)
    except Exception as e:
        logger.error(f"Portfolio refresh failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Portfolio refresh failed: {str(e)}")


@router.get("/api/position/{ticker}", response_model=PositionDetailResponse)
async def get_position_detail(ticker: str):
    """Get detailed position data including price history."""
    try:
        from main import adapter, scorer

        ticker = ticker.upper()
        analysis = await _get_analysis()

        # Find position in analysis
        position = None
        for pos in analysis.positions + analysis.etf_positions:
            if pos.ticker == ticker:
                position = pos
                break

        if position is None:
            raise HTTPException(status_code=404, detail=f"Position {ticker} not found in portfolio")

        # Fetch full price history for charting
        from main import adapter as adp
        df = adp.get_price_history(ticker, 252)
        spy_df = adp.get_price_history("SPY", 252)

        close = df["close"]
        ma20_series = sma(close, 20)
        ma50_series = sma(close, 50)

        # Build history arrays
        price_history = []
        for i, (idx, row) in enumerate(df.iterrows()):
            price_history.append({
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(float(row["close"]), 2),
                "volume": int(row["volume"]),
                "ma20": round(float(ma20_series.iloc[i]), 2),
                "ma50": round(float(ma50_series.iloc[i]), 2),
            })

        # SPY history (last 90 days normalized)
        spy_recent = spy_df.tail(90)
        spy_base = float(spy_recent["close"].iloc[0]) if not spy_recent.empty else 1.0
        spy_history = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(float(row["close"]) / spy_base * 100, 4),
            }
            for idx, row in spy_recent.iterrows()
        ]

        # Normalize stock price history for comparison (last 90 days)
        recent_df = df.tail(90)
        stock_base = float(recent_df["close"].iloc[0]) if not recent_df.empty else 1.0
        stock_normalized = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(float(row["close"]) / stock_base * 100, 4),
            }
            for idx, row in recent_df.iterrows()
        ]

        return PositionDetailResponse(
            position=position,
            price_history=price_history,
            spy_history=spy_history,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Position detail failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/holdings")
async def get_holdings():
    """Get raw holdings data."""
    holdings = _load_holdings()
    return holdings.model_dump()


@router.put("/api/holdings")
async def update_holdings(holdings: Holdings):
    """Save updated holdings and invalidate cache."""
    try:
        _save_holdings(holdings)
        _invalidate_cache()
        return {"status": "ok", "message": "Holdings saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/holdings/equity")
async def add_equity(equity: EquityHolding):
    """Add or update an equity position."""
    try:
        holdings = _load_holdings()
        # Check if already exists, update quantity
        for existing in holdings.equities:
            if existing.ticker == equity.ticker.upper():
                existing.quantity = equity.quantity
                existing.notes = equity.notes
                _save_holdings(holdings)
                _invalidate_cache()
                return {"status": "updated", "ticker": equity.ticker}

        equity.ticker = equity.ticker.upper()
        holdings.equities.append(equity)
        _save_holdings(holdings)
        _invalidate_cache()
        return {"status": "added", "ticker": equity.ticker}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/holdings/equity/{ticker}")
async def delete_equity(ticker: str):
    """Remove an equity position."""
    try:
        holdings = _load_holdings()
        ticker = ticker.upper()
        original_count = len(holdings.equities)
        holdings.equities = [e for e in holdings.equities if e.ticker != ticker]
        if len(holdings.equities) == original_count:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        _save_holdings(holdings)
        _invalidate_cache()
        return {"status": "deleted", "ticker": ticker}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
