import random
import time
import logging
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd

from adapters.base import DataAdapter

logger = logging.getLogger(__name__)

CACHE_TTL = 300

SEED_PRICES = {
    'NVDA': 115, 'AAPL': 195, 'MSFT': 375, 'META': 580, 'AMZN': 205,
    'GOOG': 170, 'SMCI': 35, 'AXP': 290, 'PANW': 175, 'NOW': 850,
    'SNOW': 125, 'PATH': 10, 'BBAI': 3, 'PINS': 28, 'BE': 18,
    'AVGO': 195, 'CRM': 290, 'FUBO': 4, 'ORCL': 155, 'AMD': 88,
    'HIMS': 28, 'RZLV': 2, 'CAKE': 48, 'VRT': 78, 'HOOD': 38,
    'TTD': 75, 'ADBE': 395, 'COIN': 195, 'HNST': 4, 'EL': 58,
    'CELH': 32, 'WYNN': 88, 'ELF': 42, 'NKE': 72, 'GME': 24,
    'T': 22, 'MARA': 14, 'SOFI': 12, 'TSLA': 245, 'PLTR': 85,
    'RIOT': 9, 'UNH': 490, 'PYPL': 62, 'IWM': 198, 'VOO': 515,
    'VTI': 258, 'URNM': 43, 'SPY': 548,
}

# High-beta tickers get higher volatility
HIGH_BETA = {'BBAI', 'FUBO', 'SOFI', 'RZLV', 'HNST', 'GME', 'MARA', 'RIOT', 'SMCI', 'PATH', 'HIMS', 'CELH'}
MID_BETA = {'NVDA', 'AMD', 'TSLA', 'COIN', 'HOOD', 'PLTR', 'TTD', 'SNOW', 'PANW', 'NOW', 'CRM', 'ADBE'}
DEFENSIVE = {'T', 'UNH', 'AXP', 'IWM', 'VOO', 'VTI', 'URNM'}

# Mock earnings windows: some near, some far
NEAR_EARNINGS = {'AMZN', 'NVDA', 'META', 'MSFT', 'AAPL', 'COIN', 'TSLA'}
MID_EARNINGS = {'PLTR', 'SNOW', 'ADBE', 'CRM', 'NOW', 'PANW', 'TTD'}

# Assign fixed seeds per ticker for reproducibility
_TICKER_SEEDS: Dict[str, int] = {}


def _get_ticker_seed(ticker: str) -> int:
    if ticker not in _TICKER_SEEDS:
        _TICKER_SEEDS[ticker] = abs(hash(ticker)) % 100000
    return _TICKER_SEEDS[ticker]


def _get_vol_drift(ticker: str) -> Tuple[float, float]:
    """Return (daily_vol, annual_drift) for a ticker."""
    if ticker in HIGH_BETA:
        return 0.035, -0.05
    elif ticker in MID_BETA:
        return 0.025, 0.12
    elif ticker in DEFENSIVE:
        return 0.008, 0.08
    else:
        return 0.018, 0.10


class MockAdapter(DataAdapter):
    def __init__(self):
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _cache_key(self, ticker: str, kind: str) -> str:
        return f"{ticker}:{kind}"

    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            ts, value = self._cache[key]
            if time.time() - ts < CACHE_TTL:
                return value
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def invalidate(self) -> None:
        self._cache.clear()

    def get_price_history(self, ticker: str, days: int = 252) -> pd.DataFrame:
        key = self._cache_key(ticker, f"history_{days}")
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        seed_price = SEED_PRICES.get(ticker, 50.0)
        daily_vol, annual_drift = _get_vol_drift(ticker)
        daily_drift = annual_drift / 252

        rng = np.random.default_rng(_get_ticker_seed(ticker))

        # Generate price path backwards from seed price
        returns = rng.normal(daily_drift, daily_vol, days)
        # Walk price forward from a start point
        start_price = seed_price / np.exp(np.sum(returns[-60:]))
        start_price = max(start_price, 0.5)

        prices = [start_price]
        for r in returns:
            prices.append(prices[-1] * np.exp(r))

        prices = prices[1:]  # drop seed

        # Build OHLCV
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        dates = []
        current = end_date - timedelta(days=days * 1.5)
        while len(dates) < days:
            if current.weekday() < 5:  # weekday only
                dates.append(current)
            current += timedelta(days=1)
        dates = dates[-days:]

        rows = []
        for i, (d, close) in enumerate(zip(dates, prices)):
            spread = close * daily_vol * 0.5
            high = close + abs(rng.normal(0, spread))
            low = close - abs(rng.normal(0, spread))
            open_ = close + rng.normal(0, spread * 0.5)
            open_ = max(open_, 0.01)
            high = max(high, close, open_)
            low = min(low, close, open_)
            # Volume: higher on big moves
            base_vol = seed_price * 1000000 / max(close, 1)
            vol = int(abs(rng.normal(base_vol, base_vol * 0.3)))
            rows.append({
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": max(vol, 1000),
            })

        df = pd.DataFrame(rows, index=pd.DatetimeIndex(dates))
        df.index.name = "date"

        self._set_cached(key, df)
        return df

    def get_earnings_date(self, ticker: str) -> Optional[date]:
        key = self._cache_key(ticker, "earnings")
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        today = date.today()
        rng = random.Random(_get_ticker_seed(ticker))

        if ticker in NEAR_EARNINGS:
            days_out = rng.randint(5, 18)
        elif ticker in MID_EARNINGS:
            days_out = rng.randint(20, 50)
        else:
            days_out = rng.randint(50, 90)

        result = today + timedelta(days=days_out)
        self._set_cached(key, result)
        return result

    def get_latest_price(self, ticker: str) -> float:
        df = self.get_price_history(ticker)
        return float(df["close"].iloc[-1])
