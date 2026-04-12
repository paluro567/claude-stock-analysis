import numpy as np
import pandas as pd
from typing import Optional


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=period, min_periods=1).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False, min_periods=1).mean()


def rsi(series: pd.Series, period: int = 14) -> float:
    """
    Returns the latest RSI value (0-100).
    Uses Wilder's smoothing method.
    """
    if len(series) < period + 1:
        return 50.0

    delta = series.diff().dropna()
    gains = delta.clip(lower=0)
    losses = (-delta).clip(lower=0)

    avg_gain = gains.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False).mean()

    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]

    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return float(100 - 100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def drawdown_from_peak(series: pd.Series, lookback: int = 60) -> float:
    """
    Returns the percentage drawdown from the peak over the lookback window.
    Positive number means price is below peak.
    """
    recent = series.iloc[-lookback:] if len(series) >= lookback else series
    if recent.empty:
        return 0.0
    peak = recent.max()
    current = recent.iloc[-1]
    if peak <= 0:
        return 0.0
    dd = (peak - current) / peak * 100
    return float(max(dd, 0.0))


def ma_slope(series: pd.Series, ma_period: int = 50, lookback: int = 20) -> float:
    """
    Returns the slope of the MA over the last `lookback` sessions as a percentage.
    Positive means rising MA.
    """
    ma_series = sma(series, ma_period)
    if len(ma_series) < lookback + ma_period:
        available = len(ma_series)
        if available < 2:
            return 0.0
        lookback = min(lookback, available - 1)

    ma_today = ma_series.iloc[-1]
    ma_ago = ma_series.iloc[-(lookback + 1)]

    if ma_ago <= 0:
        return 0.0
    slope_pct = (ma_today - ma_ago) / ma_ago * 100
    return float(slope_pct)


def gap_count(open_: pd.Series, close: pd.Series, lookback: int = 20, threshold: float = 0.02) -> int:
    """
    Count overnight gaps exceeding `threshold` (2% default) in last `lookback` sessions.
    A gap is when open is > threshold% away from prior close.
    """
    if len(close) < 2:
        return 0

    recent_close = close.iloc[-lookback - 1:-1] if len(close) > lookback else close.iloc[:-1]
    recent_open = open_.iloc[-lookback:] if len(open_) >= lookback else open_.iloc[1:]

    # Align
    min_len = min(len(recent_close), len(recent_open))
    if min_len == 0:
        return 0

    recent_close = recent_close.iloc[-min_len:]
    recent_open = recent_open.iloc[-min_len:]

    gap_pct = (recent_open.values - recent_close.values) / (recent_close.values + 1e-10)
    count = int(np.sum(np.abs(gap_pct) > threshold))
    return count


def compute_rsi_series(series: pd.Series, period: int = 14) -> pd.Series:
    """Returns full RSI series for trend analysis."""
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = (-delta).clip(lower=0)

    avg_gain = gains.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-10)
    rsi_series = 100 - 100 / (1 + rs)
    return rsi_series
