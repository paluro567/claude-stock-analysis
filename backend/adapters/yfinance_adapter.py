import time
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, Tuple
import pandas as pd
import yfinance as yf

from adapters.base import DataAdapter

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes


class YFinanceAdapter(DataAdapter):
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

        try:
            t = yf.Ticker(ticker)
            # Use period '1y' for up to 252 trading days
            period = "1y" if days <= 252 else "2y"
            df = t.history(period=period)

            if df.empty:
                raise ValueError(f"No data returned for {ticker}")

            # Normalize columns
            df = df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            })
            df = df[["open", "high", "low", "close", "volume"]].copy()
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df = df.sort_index()

            # Keep only last `days` rows
            if len(df) > days:
                df = df.iloc[-days:]

            self._set_cached(key, df)
            return df

        except Exception as e:
            logger.warning(f"YFinance error for {ticker}: {e}")
            raise

    def get_earnings_date(self, ticker: str) -> Optional[date]:
        key = self._cache_key(ticker, "earnings")
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is None:
                return None

            # calendar can be a dict or DataFrame depending on version
            if isinstance(cal, dict):
                earnings_date = cal.get("Earnings Date")
                if earnings_date:
                    if hasattr(earnings_date, '__iter__') and not isinstance(earnings_date, str):
                        earnings_date = list(earnings_date)[0]
                    if hasattr(earnings_date, 'date'):
                        result = earnings_date.date()
                    else:
                        result = datetime.strptime(str(earnings_date)[:10], "%Y-%m-%d").date()
                    self._set_cached(key, result)
                    return result
            elif hasattr(cal, 'loc'):
                # DataFrame format
                if 'Earnings Date' in cal.index:
                    ed = cal.loc['Earnings Date'].iloc[0]
                    if hasattr(ed, 'date'):
                        result = ed.date()
                        self._set_cached(key, result)
                        return result

            self._set_cached(key, None)
            return None

        except Exception as e:
            logger.warning(f"Could not get earnings date for {ticker}: {e}")
            self._set_cached(key, None)
            return None

    def get_latest_price(self, ticker: str) -> float:
        df = self.get_price_history(ticker)
        return float(df["close"].iloc[-1])
