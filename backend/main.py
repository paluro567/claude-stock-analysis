from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import math
import time
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── TTL Cache — 1 hour for valuation data (barely changes intraday) ────────────
_cache: dict = {}
CACHE_TTL_SECONDS = 3600


#data become "stale" after 60 minutes
def cache_get(key: str):
    entry = _cache.get(key)
    if entry and datetime.now() - entry["ts"] < timedelta(seconds=CACHE_TTL_SECONDS):
        return entry["data"]
    return None

def cache_set(key: str, data):
    _cache[key] = {"data": data, "ts": datetime.now()}


# ── Sector reference data ──────────────────────────────────────────────────────
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

# ── Helpers ────────────────────────────────────────────────────────────────────
def safe_float(value):
    if value is None:
        return None
    try:
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def fetch_info(ticker_obj, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            info = ticker_obj.info or {}
            # Validate we got a meaningful response — not just a stub from rate limiting
            has_data = any([
                info.get('regularMarketPrice'),
                info.get('currentPrice'),
                info.get('marketCap'),
                info.get('trailingPE'),
                info.get('longName'),
            ])
            if not has_data:
                raise ValueError("sparse")
            return info
        except Exception as e:
            msg = str(e).lower()
            is_retryable = any(x in msg for x in ("too many", "rate", "429", "sparse"))
            if attempt < retries - 1 and is_retryable:
                time.sleep(2 ** attempt)
                continue
            raise
    return {}


# ── Main stock endpoint — valuation data only, no intraday ────────────────────
@app.get("/api/stock/{ticker}")
async def get_stock(ticker: str):
    ticker = ticker.upper().strip()

    cached = cache_get(ticker)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = fetch_info(t)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch {ticker}: {str(e)}")

    current_price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    previous_close = safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
    day_high = safe_float(info.get("dayHigh") or info.get("regularMarketDayHigh"))
    day_low = safe_float(info.get("dayLow") or info.get("regularMarketDayLow"))
    fifty_two_week_high = safe_float(info.get("fiftyTwoWeekHigh"))
    fifty_two_week_low = safe_float(info.get("fiftyTwoWeekLow"))
    trailing_pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    peg_ratio = safe_float(info.get("pegRatio"))
    price_to_book = safe_float(info.get("priceToBook"))
    price_to_sales = safe_float(info.get("priceToSalesTrailing12Months"))
    eps_trailing = safe_float(info.get("trailingEps"))
    eps_forward = safe_float(info.get("forwardEps"))
    sector = info.get("sector") or None
    industry = info.get("industry") or None
    market_cap = safe_float(info.get("marketCap"))
    sector_pe = SECTOR_PE.get(sector) if sector else None

    # 2-year forward PE from next-year EPS estimate
    two_year_forward_pe = None
    try:
        earnings_est = t.earnings_estimate
        if earnings_est is not None and "Next Year" in earnings_est.index:
            ny_eps = safe_float(earnings_est.loc["Next Year", "avg"])
            if ny_eps and ny_eps > 0 and current_price:
                two_year_forward_pe = round(current_price / ny_eps, 2)
    except Exception:
        pass

    # Overvaluation score vs sector
    ovval_pct = None
    if trailing_pe and sector_pe:
        ovval_pct = round(((trailing_pe - sector_pe) / sector_pe) * 100, 1)

    # Growth
    revenue_growth = safe_float(info.get('revenueGrowth'))
    earnings_growth = safe_float(info.get('earningsGrowth'))
    # FCF growth — best effort from cashflow statement
    fcf_growth = None
    try:
        cf = t.cashflow
        if cf is not None and not cf.empty:
            if 'Free Cash Flow' in cf.index:
                vals = cf.loc['Free Cash Flow'].dropna()
            else:
                ocf = cf.loc['Operating Cash Flow'] if 'Operating Cash Flow' in cf.index else None
                capex = cf.loc['Capital Expenditure'] if 'Capital Expenditure' in cf.index else None
                if ocf is not None and capex is not None:
                    vals = ocf + capex
                else:
                    vals = None
            if vals is not None and len(vals) >= 2:
                curr, prev = float(vals.iloc[0]), float(vals.iloc[1])
                if prev != 0:
                    fcf_growth = round((curr - prev) / abs(prev), 4)
    except Exception:
        pass

    # Profitability
    gross_margins = safe_float(info.get('grossMargins'))
    operating_margins = safe_float(info.get('operatingMargins'))
    return_on_equity = safe_float(info.get('returnOnEquity'))

    # Balance sheet
    debt_to_equity = safe_float(info.get('debtToEquity'))
    current_ratio = safe_float(info.get('currentRatio'))

    # Momentum
    held_pct_institutions = safe_float(info.get('heldPercentInstitutions'))
    week52_change = safe_float(info.get('52WeekChange'))
    sp52_change = safe_float(info.get('SandP52WeekChange'))
    relative_strength = round(week52_change - sp52_change, 4) if week52_change is not None and sp52_change is not None else None
    avg_volume = info.get('averageVolume')
    avg_volume_10d = info.get('averageDailyVolume10Day')
    volume_trend = round((avg_volume_10d / avg_volume) - 1, 4) if avg_volume and avg_volume_10d else None

    result = {
        "name": info.get("longName") or info.get("shortName") or ticker,
        "ticker": ticker,
        "currentPrice": current_price,
        "previousClose": previous_close,
        "dayHigh": day_high,
        "dayLow": day_low,
        "fiftyTwoWeekHigh": fifty_two_week_high,
        "fiftyTwoWeekLow": fifty_two_week_low,
        "trailingPE": trailing_pe,
        "forwardPE": forward_pe,
        "twoYearForwardPE": two_year_forward_pe,
        "pegRatio": peg_ratio,
        "priceToBook": price_to_book,
        "priceToSales": price_to_sales,
        "trailingEps": eps_trailing,
        "forwardEps": eps_forward,
        "sector": sector,
        "industry": industry,
        "marketCap": market_cap,
        "sectorPE": sector_pe,
        "overvaluationPct": ovval_pct,
        "peers": [],
        "revenueGrowth": revenue_growth,
        "earningsGrowth": earnings_growth,
        "fcfGrowth": fcf_growth,
        "grossMargins": gross_margins,
        "operatingMargins": operating_margins,
        "returnOnEquity": return_on_equity,
        "debtToEquity": debt_to_equity,
        "currentRatio": current_ratio,
        "heldPercentInstitutions": held_pct_institutions,
        "week52Change": week52_change,
        "relativeStrength": relative_strength,
        "volumeTrend": volume_trend,
    }

    # Only cache if we received real data — prevents caching rate-limited empty responses
    if any([current_price, trailing_pe, market_cap]):
        cache_set(ticker, result)

    return result


# ── Peers endpoint — bulk fetch, cached separately ────────────────────────────
@app.get("/api/stock/{ticker}/peers")
async def get_peers(ticker: str):
    ticker = ticker.upper().strip()
    cache_key = f"{ticker}:peers"

    cached = cache_get(cache_key)
    if cached:
        return cached

    main = cache_get(ticker)
    sector = main["sector"] if main else None

    if not sector:
        try:
            info = fetch_info(yf.Ticker(ticker))
            sector = info.get("sector")
        except Exception:
            return {"peers": []}

    if not sector or sector not in SECTOR_PEERS:
        return {"peers": []}

    peer_tickers = [p for p in SECTOR_PEERS[sector] if p != ticker][:4]

    peers = []
    try:
        bulk = yf.Tickers(" ".join(peer_tickers))
        for pt in peer_tickers:
            try:
                pi = bulk.tickers[pt].info or {}
                peers.append({
                    "ticker": pt,
                    "name": pi.get("longName") or pi.get("shortName") or pt,
                    "trailingPE": safe_float(pi.get("trailingPE")),
                    "forwardPE": safe_float(pi.get("forwardPE")),
                    "priceToBook": safe_float(pi.get("priceToBook")),
                })
            except Exception:
                peers.append({"ticker": pt, "name": pt, "trailingPE": None, "forwardPE": None, "priceToBook": None})
    except Exception:
        for pt in peer_tickers:
            peers.append({"ticker": pt, "name": pt, "trailingPE": None, "forwardPE": None, "priceToBook": None})

    result = {"peers": peers}
    cache_set(cache_key, result)
    return result


@app.get("/api/cache/status")
async def cache_status():
    return {"entries": len(_cache), "keys": list(_cache.keys())}
