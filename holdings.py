"""
holdings.py — Single source of truth for portfolio holdings and mock OHLCV generation.

Imported by both main.py (CLI) and api.py (FastAPI).  To change the portfolio,
edit PORTFOLIO_SPECS only — both runtime paths update automatically.

Portfolio: 43 equities · 4 ETFs · 2 options = 49 positions

Quantities are real (from portfolio input).
Prices, drift, and volatility are synthetic mock parameters seeded per ticker.
Options: AMZN CALLs expiring 2027-01-15 (strikes 190 and 210).
         days_to_earnings = DTE from 2026-04-12 → 2027-01-15 ≈ 278 days.
"""

import hashlib
import random


# ---------------------------------------------------------------------------
# Mock OHLCV generator — deterministic, seeded per ticker
# ---------------------------------------------------------------------------

def generate_ohlcv(
    ticker:    str,
    days:      int,
    base:      float,
    drift:     float,
    daily_vol: float,
) -> dict:
    """
    Synthetic OHLCV for `days` sessions, descending (index 0 = today).
    RNG seeded from MD5(ticker) for full determinism.
    """
    seed = int(hashlib.md5(ticker.encode()).hexdigest(), 16) % (2 ** 32)
    rng  = random.Random(seed)

    closes = [base]
    for _ in range(days - 1):
        closes.append(closes[-1] * (1.0 + rng.gauss(drift, daily_vol)))

    opens, highs, lows, volumes = [], [], [], []
    prev_close = closes[0]
    for c in closes:
        gap    = rng.gauss(0.0, daily_vol * 0.3)
        open_  = prev_close * (1.0 + gap)
        hi_raw = open_ * (1.0 + abs(rng.gauss(0.0, daily_vol * 0.5)))
        lo_raw = open_ * (1.0 - abs(rng.gauss(0.0, daily_vol * 0.5)))
        high   = max(c, open_, hi_raw)
        low    = min(c, open_, lo_raw)
        base_v = 1_000_000 * (base / 100.0)
        vol    = max(100_000.0, rng.gauss(base_v, base_v * 0.30))
        opens.append(open_)
        highs.append(high)
        lows.append(low)
        volumes.append(vol)
        prev_close = c

    return {
        "open":   opens[::-1],
        "high":   highs[::-1],
        "low":    lows[::-1],
        "close":  closes[::-1],
        "volume": volumes[::-1],
    }


# ---------------------------------------------------------------------------
# Portfolio specification
# ---------------------------------------------------------------------------

DEFAULT_DAYS = 90   # sessions of history for equities and ETFs

# Schema per entry:
#   ticker            str            symbol (cluster lookup uses this key)
#   asset_type        str            "equity" | "etf" | "option"
#   quantity          int/float      shares or contracts held (real from portfolio)
#   days_to_earnings  int | None     earnings DTE; expiry DTE for options
#   base              float          synthetic starting price
#   drift             float          per-session drift
#   vol               float          per-session volatility
#   days              int            sessions of history to generate

PORTFOLIO_SPECS: list = [

    # =========================================================================
    # EQUITIES — 43 positions (quantities from real portfolio input)
    # =========================================================================

    # AI Semiconductors / Hardware
    dict(ticker="NVDA",  asset_type="equity", quantity=20,   days_to_earnings=12,
         base=750.0,  drift=+0.0008, vol=0.025, days=DEFAULT_DAYS),
    dict(ticker="AMD",   asset_type="equity", quantity=13,   days_to_earnings=None,
         base=115.0,  drift=+0.0002, vol=0.030, days=DEFAULT_DAYS),
    dict(ticker="AVGO",  asset_type="equity", quantity=6,    days_to_earnings=None,
         base=165.0,  drift=+0.0002, vol=0.022, days=DEFAULT_DAYS),
    dict(ticker="SMCI",  asset_type="equity", quantity=15,   days_to_earnings=None,
         base=35.0,   drift=+0.0003, vol=0.060, days=DEFAULT_DAYS),
    dict(ticker="VRT",   asset_type="equity", quantity=3,    days_to_earnings=None,
         base=80.0,   drift=+0.0004, vol=0.045, days=DEFAULT_DAYS),

    # Mega Cap
    dict(ticker="AAPL",  asset_type="equity", quantity=8,    days_to_earnings=None,
         base=215.0,  drift=+0.0001, vol=0.015, days=DEFAULT_DAYS),
    dict(ticker="MSFT",  asset_type="equity", quantity=3,    days_to_earnings=None,
         base=390.0,  drift=+0.0002, vol=0.015, days=DEFAULT_DAYS),
    dict(ticker="AMZN",  asset_type="equity", quantity=82,   days_to_earnings=None,
         base=200.0,  drift=+0.0002, vol=0.018, days=DEFAULT_DAYS),
    dict(ticker="GOOG",  asset_type="equity", quantity=12,   days_to_earnings=None,
         base=180.0,  drift=+0.0001, vol=0.018, days=DEFAULT_DAYS),
    dict(ticker="META",  asset_type="equity", quantity=8,    days_to_earnings=None,
         base=560.0,  drift=+0.0003, vol=0.022, days=DEFAULT_DAYS),
    dict(ticker="UNH",   asset_type="equity", quantity=19,   days_to_earnings=None,
         base=480.0,  drift=+0.0001, vol=0.018, days=DEFAULT_DAYS),

    # AI / Enterprise Software
    dict(ticker="NOW",   asset_type="equity", quantity=35,   days_to_earnings=None,
         base=900.0,  drift=+0.0003, vol=0.020, days=DEFAULT_DAYS),
    dict(ticker="CRM",   asset_type="equity", quantity=63,   days_to_earnings=None,
         base=290.0,  drift=+0.0002, vol=0.022, days=DEFAULT_DAYS),
    dict(ticker="SNOW",  asset_type="equity", quantity=10,   days_to_earnings=None,
         base=145.0,  drift=+0.0001, vol=0.035, days=DEFAULT_DAYS),
    dict(ticker="ADBE",  asset_type="equity", quantity=44,   days_to_earnings=None,
         base=380.0,  drift=+0.0000, vol=0.020, days=DEFAULT_DAYS),
    dict(ticker="ORCL",  asset_type="equity", quantity=4,    days_to_earnings=None,
         base=135.0,  drift=+0.0002, vol=0.018, days=DEFAULT_DAYS),
    dict(ticker="PANW",  asset_type="equity", quantity=3,    days_to_earnings=None,
         base=170.0,  drift=+0.0002, vol=0.022, days=DEFAULT_DAYS),
    dict(ticker="TTD",   asset_type="equity", quantity=30,   days_to_earnings=None,
         base=100.0,  drift=+0.0003, vol=0.035, days=DEFAULT_DAYS),

    # Speculative Growth / AI Small Cap
    dict(ticker="BBAI",  asset_type="equity", quantity=250,  days_to_earnings=60,
         base=3.5,    drift=-0.0003, vol=0.055, days=DEFAULT_DAYS),
    dict(ticker="PLTR",  asset_type="equity", quantity=49,   days_to_earnings=None,
         base=80.0,   drift=+0.0006, vol=0.045, days=DEFAULT_DAYS),
    dict(ticker="PATH",  asset_type="equity", quantity=660,  days_to_earnings=None,
         base=14.0,   drift=+0.0001, vol=0.045, days=DEFAULT_DAYS),
    dict(ticker="FUBO",  asset_type="equity", quantity=25,   days_to_earnings=None,
         base=4.5,    drift=-0.0002, vol=0.075, days=DEFAULT_DAYS),
    dict(ticker="HIMS",  asset_type="equity", quantity=37,   days_to_earnings=None,
         base=22.0,   drift=+0.0004, vol=0.055, days=DEFAULT_DAYS),
    dict(ticker="RZLV",  asset_type="equity", quantity=642,  days_to_earnings=None,
         base=2.5,    drift=-0.0002, vol=0.080, days=DEFAULT_DAYS),
    dict(ticker="HNST",  asset_type="equity", quantity=2800, days_to_earnings=None,
         base=4.5,    drift=+0.0001, vol=0.055, days=DEFAULT_DAYS),
    dict(ticker="SOFI",  asset_type="equity", quantity=145,  days_to_earnings=None,
         base=13.0,   drift=+0.0002, vol=0.050, days=DEFAULT_DAYS),
    dict(ticker="GME",   asset_type="equity", quantity=1,    days_to_earnings=None,
         base=26.0,   drift=-0.0001, vol=0.065, days=DEFAULT_DAYS),

    # Crypto-Linked
    dict(ticker="COIN",  asset_type="equity", quantity=12,   days_to_earnings=None,
         base=235.0,  drift=+0.0007, vol=0.065, days=DEFAULT_DAYS),
    dict(ticker="MARA",  asset_type="equity", quantity=292,  days_to_earnings=None,
         base=15.0,   drift=+0.0005, vol=0.075, days=DEFAULT_DAYS),
    dict(ticker="RIOT",  asset_type="equity", quantity=52,   days_to_earnings=None,
         base=8.0,    drift=+0.0004, vol=0.080, days=DEFAULT_DAYS),
    dict(ticker="HOOD",  asset_type="equity", quantity=15,   days_to_earnings=None,
         base=38.0,   drift=+0.0004, vol=0.055, days=DEFAULT_DAYS),

    # Consumer Discretionary / Retail
    dict(ticker="CAKE",  asset_type="equity", quantity=95,   days_to_earnings=None,
         base=36.0,   drift=+0.0001, vol=0.025, days=DEFAULT_DAYS),
    dict(ticker="EL",    asset_type="equity", quantity=20,   days_to_earnings=None,
         base=65.0,   drift=-0.0002, vol=0.025, days=DEFAULT_DAYS),
    dict(ticker="CELH",  asset_type="equity", quantity=120,  days_to_earnings=None,
         base=25.0,   drift=-0.0003, vol=0.045, days=DEFAULT_DAYS),
    dict(ticker="WYNN",  asset_type="equity", quantity=20,   days_to_earnings=None,
         base=85.0,   drift=+0.0001, vol=0.025, days=DEFAULT_DAYS),
    dict(ticker="ELF",   asset_type="equity", quantity=25,   days_to_earnings=None,
         base=50.0,   drift=-0.0002, vol=0.040, days=DEFAULT_DAYS),
    dict(ticker="NKE",   asset_type="equity", quantity=95,   days_to_earnings=None,
         base=72.0,   drift=-0.0001, vol=0.020, days=DEFAULT_DAYS),
    dict(ticker="PINS",  asset_type="equity", quantity=80,   days_to_earnings=None,
         base=35.0,   drift=+0.0002, vol=0.030, days=DEFAULT_DAYS),

    # Other / Cross-sector
    dict(ticker="TSLA",  asset_type="equity", quantity=17,   days_to_earnings=None,
         base=280.0,  drift=+0.0004, vol=0.040, days=DEFAULT_DAYS),
    dict(ticker="PYPL",  asset_type="equity", quantity=57,   days_to_earnings=None,
         base=75.0,   drift=+0.0001, vol=0.028, days=DEFAULT_DAYS),
    dict(ticker="AXP",   asset_type="equity", quantity=1,    days_to_earnings=None,
         base=260.0,  drift=+0.0001, vol=0.018, days=DEFAULT_DAYS),
    dict(ticker="T",     asset_type="equity", quantity=40,   days_to_earnings=None,
         base=22.0,   drift=+0.0001, vol=0.015, days=DEFAULT_DAYS),
    dict(ticker="BE",    asset_type="equity", quantity=3,    days_to_earnings=None,
         base=25.0,   drift=+0.0003, vol=0.040, days=DEFAULT_DAYS),

    # =========================================================================
    # ETFs — 4 positions (quantities from real portfolio input)
    # =========================================================================

    dict(ticker="IWM",   asset_type="etf",    quantity=26,   days_to_earnings=None,
         base=205.0,  drift=+0.0002, vol=0.013, days=DEFAULT_DAYS),
    dict(ticker="VOO",   asset_type="etf",    quantity=7,    days_to_earnings=None,
         base=510.0,  drift=+0.0003, vol=0.010, days=DEFAULT_DAYS),
    dict(ticker="VTI",   asset_type="etf",    quantity=18,   days_to_earnings=None,
         base=270.0,  drift=+0.0003, vol=0.010, days=DEFAULT_DAYS),
    dict(ticker="URNM",  asset_type="etf",    quantity=18,   days_to_earnings=None,
         base=40.0,   drift=+0.0002, vol=0.030, days=DEFAULT_DAYS),

    # =========================================================================
    # Options — 2 positions
    # Both are AMZN CALLs expiring 2027-01-15.
    # DTE from 2026-04-12 → 2027-01-15 ≈ 278 days.
    # quantity = contracts × 100 (option multiplier) for correct portfolio weighting.
    # Prices are approximate LEAPS premiums for reference.
    # Limited history (55 days) → warning DQ expected.
    # =========================================================================

    dict(ticker="AMZN_C190", asset_type="option", quantity=100, days_to_earnings=278,
         base=38.0,   drift=-0.0005, vol=0.070, days=55),
    dict(ticker="AMZN_C210", asset_type="option", quantity=200, days_to_earnings=278,
         base=28.0,   drift=-0.0006, vol=0.075, days=55),
]

SPY_SPEC = dict(ticker="SPY", base=480.0, drift=+0.0003, vol=0.010)


# ---------------------------------------------------------------------------
# Public build functions
# ---------------------------------------------------------------------------

def build_holdings() -> list:
    """
    Generate OHLCV for every spec and return a list of holding dicts
    ready to pass directly to run_engine().
    """
    holdings = []
    for spec in PORTFOLIO_SPECS:
        ohlcv = generate_ohlcv(
            ticker    = spec["ticker"],
            days      = spec["days"],
            base      = spec["base"],
            drift     = spec["drift"],
            daily_vol = spec["vol"],
        )
        holdings.append({
            "ticker":           spec["ticker"],
            "asset_type":       spec["asset_type"],
            "quantity":         spec["quantity"],
            "days_to_earnings": spec["days_to_earnings"],
            "ohlcv":            ohlcv,
        })
    return holdings


def build_spy() -> dict:
    """Generate SPY benchmark OHLCV at DEFAULT_DAYS depth."""
    s = SPY_SPEC
    return generate_ohlcv(
        ticker    = s["ticker"],
        days      = DEFAULT_DAYS,
        base      = s["base"],
        drift     = s["drift"],
        daily_vol = s["vol"],
    )
