"""
indicators.py — Core technical indicator functions.

Array convention: ALL arrays are DESCENDING — index 0 = today, index 1 = yesterday, etc.
No external dependencies (pure Python stdlib only).
"""

from typing import Optional


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, float(value)))


def compute_sma(values: list, period: int) -> Optional[float]:
    """
    Simple moving average of the first `period` elements.
    Returns None if insufficient data.
    Descending array: values[0] = most recent.
    """
    if len(values) < period:
        return None
    return sum(values[:period]) / period


def compute_wilder_rsi(close: list, period: int = 14) -> float:
    """
    Wilder's RSI per Ambiguity 1 spec.

    Descending array (close[0] = today, close[1] = yesterday).
    Changes computed as close[i-1] - close[i]  (older minus newer = daily change).

    Seeding: if history < 2*period, use simple mean of available gains/losses (no Wilder smoothing).
    Otherwise: seed with mean of first `period` changes, then Wilder-smooth through older data.

    Returns 50.0 if insufficient data (< period bars).
    """
    n = len(close)
    if n < period:
        return 50.0

    # changes[i] = close[i-1] - close[i] = gain if positive, loss if negative
    # Index 0 of changes = most recent day's change (close[0] today vs close[1] yesterday)
    changes = [close[i - 1] - close[i] for i in range(1, n)]
    gains  = [max(0.0,  c) for c in changes]
    losses = [max(0.0, -c) for c in changes]

    if len(changes) < period:
        # Not enough for even one seed window; return neutral
        return 50.0

    if n < 2 * period:
        # Insufficient history for Wilder smoothing — use simple average of available bars
        seed_n = min(period, len(gains))
        avg_gain = sum(gains[:seed_n]) / seed_n
        avg_loss = sum(losses[:seed_n]) / seed_n
    else:
        # Seed with mean of first `period` changes (index 0..period-1 = most recent changes)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        # Wilder-smooth through older (higher-index) changes
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_atr(high: list, low: list, close: list, start: int, end: int) -> float:
    """
    Simple mean of True Range over indices [start, end).
    Per Ambiguity 2: close[i+1] is the prior close (descending array).

    True Range = max(high[i]-low[i], |high[i]-close[i+1]|, |low[i]-close[i+1]|)

    Returns 0.0 if no valid bars computed.
    """
    trs = []
    for i in range(start, end):
        if i + 1 >= len(close):
            break
        prior_close = close[i + 1]
        tr = max(
            high[i] - low[i],
            abs(high[i] - prior_close),
            abs(low[i]  - prior_close),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def percentile_rank(value: float, population: list) -> float:
    """
    Midpoint percentile rank of `value` within `population`.
    Formula: (below + 0.5 * equal) / n
    Returns 0.5 if population has only 1 element (no cross-portfolio context).
    """
    n = len(population)
    if n <= 1:
        return 0.5
    below = sum(1 for x in population if x < value)
    equal = sum(1 for x in population if x == value)
    return (below + 0.5 * equal) / n
