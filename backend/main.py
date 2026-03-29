from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from typing import Optional
import math
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECTOR_PE = {
    "Technology": 28,
    "Healthcare": 22,
    "Financial Services": 14,
    "Consumer Cyclical": 20,
    "Consumer Defensive": 18,
    "Energy": 12,
    "Utilities": 17,
    "Real Estate": 35,
    "Basic Materials": 15,
    "Communication Services": 20,
    "Industrials": 20,
}

SECTOR_PEERS = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA"],
    "Healthcare": ["JNJ", "UNH", "PFE", "ABT"],
    "Financial Services": ["JPM", "BAC", "GS", "MS"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE"],
    "Consumer Defensive": ["PG", "KO", "WMT", "COST"],
    "Energy": ["XOM", "CVX", "COP", "SLB"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS"],
    "Industrials": ["GE", "HON", "CAT", "BA"],
    "Real Estate": ["AMT", "PLD", "SPG", "O"],
    "Utilities": ["NEE", "DUK", "SO", "AEP"],
    "Basic Materials": ["LIN", "APD", "ECL", "SHW"],
}


def safe_float(value):
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


@app.get("/api/stock/{ticker}")
async def get_stock(ticker: str):
    ticker = ticker.upper().strip()
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ticker info: {str(e)}")

    # Basic price info
    current_price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    previous_close = safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
    day_high = safe_float(info.get("dayHigh") or info.get("regularMarketDayHigh"))
    day_low = safe_float(info.get("dayLow") or info.get("regularMarketDayLow"))

    # Pivot points from previous day OHLC
    prev_high = safe_float(info.get("regularMarketDayHigh") or day_high)
    prev_low = safe_float(info.get("regularMarketDayLow") or day_low)
    prev_close = previous_close

    pivot = r1 = s1 = r2 = s2 = None
    if prev_high is not None and prev_low is not None and prev_close is not None:
        pivot = (prev_high + prev_low + prev_close) / 3
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)

    # 2-year forward PE from next year EPS estimate
    two_year_forward_pe = None
    try:
        earnings_est = t.earnings_estimate
        if earnings_est is not None and 'Next Year' in earnings_est.index:
            next_year_eps = safe_float(earnings_est.loc['Next Year', 'avg'])
            if next_year_eps and next_year_eps > 0 and current_price:
                two_year_forward_pe = round(current_price / next_year_eps, 2)
    except Exception:
        pass

    # Intraday 5m data
    intraday = []
    try:
        hist = t.history(period="1d", interval="5m")
        if hist is not None and not hist.empty:
            for ts, row in hist.iterrows():
                intraday.append({
                    "time": ts.strftime("%H:%M"),
                    "open": safe_float(row.get("Open")),
                    "high": safe_float(row.get("High")),
                    "low": safe_float(row.get("Low")),
                    "close": safe_float(row.get("Close")),
                })
    except Exception:
        intraday = []

    # Fundamentals
    trailing_pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    sector = info.get("sector") or None
    industry = info.get("industry") or None
    market_cap = safe_float(info.get("marketCap"))
    name = info.get("longName") or info.get("shortName") or ticker

    sector_pe = SECTOR_PE.get(sector) if sector else None

    # Peers
    peers = []
    if sector and sector in SECTOR_PEERS:
        peer_tickers = [p for p in SECTOR_PEERS[sector] if p != ticker][:4]
        for peer_ticker in peer_tickers:
            time.sleep(0.5)
            try:
                pt = yf.Ticker(peer_ticker)
                pi = pt.info or {}
                peers.append({
                    "ticker": peer_ticker,
                    "name": pi.get("longName") or pi.get("shortName") or peer_ticker,
                    "trailingPE": safe_float(pi.get("trailingPE")),
                    "forwardPE": safe_float(pi.get("forwardPE")),
                })
            except Exception:
                peers.append({
                    "ticker": peer_ticker,
                    "name": peer_ticker,
                    "trailingPE": None,
                    "forwardPE": None,
                })

    return {
        "name": name,
        "ticker": ticker,
        "currentPrice": current_price,
        "previousClose": previous_close,
        "dayHigh": day_high,
        "dayLow": day_low,
        "pivot": pivot,
        "r1": r1,
        "s1": s1,
        "r2": r2,
        "s2": s2,
        "intraday": intraday,
        "trailingPE": trailing_pe,
        "forwardPE": forward_pe,
        "sector": sector,
        "industry": industry,
        "marketCap": market_cap,
        "sectorPE": sector_pe,
        "twoYearForwardPE": two_year_forward_pe,
        "peers": peers,
    }
