"""
formulas.py — Phase 1 constants, Strength Score, Risk Score, Exposure + Trim,
              Upside Score (UV), Recovery Confidence (RC), Setup Integrity (SIS),
              and Add Score formulas.

All arrays descending (index 0 = today). Pure Python, no external dependencies.
"""

from typing import Optional
from indicators import clamp, compute_sma, compute_wilder_rsi, compute_atr, percentile_rank

# ---------------------------------------------------------------------------
# Global Constants — Strength Score
# ---------------------------------------------------------------------------

STRENGTH_WEIGHTS = {
    "rel_perf":     0.30,
    "trend_pos":    0.25,
    "trend_struct": 0.20,
    "vol_conf":     0.15,
    "stability":    0.10,
}

HYBRID_ALPHA_N_LT_8    = 0.00
HYBRID_ALPHA_N_8_TO_14 = 0.50
HYBRID_ALPHA_N_GTE_15  = 0.65

REL_PERF_ABS_MIN   = -0.10
REL_PERF_ABS_RANGE =  0.20

TREND_POS_S20_WEIGHT    = 0.60
TREND_POS_STACK_WEIGHT  = 0.40
TREND_POS_S20_DENOM     = 0.10
TREND_POS_STACK_DENOM   = 0.05
TREND_POS_SCALE         = 50.0
TREND_POS_OFFSET        = 50.0
TREND_POS_EXT_THRESHOLD   = 0.07
TREND_POS_EXT_SCALE       = 350.0
TREND_POS_EXT_PENALTY_CAP = 25.0

TREND_STRUCT_ABS_MIN   = -0.02
TREND_STRUCT_ABS_RANGE =  0.04

MIN_HISTORY_MA20    = 20
MIN_HISTORY_MA50    = 50
MIN_HISTORY_FULL    = 70

FALLBACK_NEUTRAL = 50.0

VOL_CONF_LOOKBACK = 40

STABILITY_ATR_CURRENT_PERIOD  = 14
STABILITY_ATR_BASELINE_PERIOD = 14
STABILITY_ATR_BASELINE_START  = 29

SMOOTHING_ALPHA = 0.40

# ---------------------------------------------------------------------------
# Global Constants — Risk Score
# ---------------------------------------------------------------------------

RISK_WEIGHTS = {
    "overext":     0.25,
    "rsi_stretch": 0.20,
    "event_risk":  0.20,
    "vol_exp":     0.15,
    "accel":       0.10,
    "gap_risk":    0.10,
}

OVEREXT_SCALE = 600.0

VOL_EXP_NEUTRAL_RATIO = 0.5
VOL_EXP_SCALE         = 80.0
MIN_HISTORY_ATR14     = 15
MIN_HISTORY_ATR50     = 51

ACCEL_SCALE       = 60.0
ACCEL_EPSILON     = 1e-6
MIN_HISTORY_ACCEL = 31

GAP_RISK_LOOKBACK    = 20
GAP_RISK_THRESHOLD   = 0.02
GAP_RISK_PER_GAP     = 18.0
MIN_HISTORY_GAP_RISK = 2

EVENT_RISK_THRESHOLDS = [
    (7,  100.0),
    (14,  80.0),
    (21,  60.0),
    (45,  30.0),
    (90,  15.0),
]
EVENT_RISK_DEFAULT = 5.0

# ---------------------------------------------------------------------------
# Global Constants — Exposure Score
# ---------------------------------------------------------------------------

CLUSTERS = {
    "AI_SEMIS":      ["NVDA", "AMD", "AVGO", "SMCI", "INTC", "QCOM", "MRVL", "ARM"],
    "CRYPTO_LINKED": ["MSTR", "COIN", "RIOT", "MARA", "HUT", "CLSK", "HOOD"],
    "SPEC_GROWTH":   ["BBAI", "PLTR", "AI", "SOUN", "IONQ", "RXRX", "FUBO", "SOFI",
                      "RZLV", "HNST", "HIMS", "GME", "PATH"],
    "MEGA_CAP":      ["AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "NVDA",
                      "BRK.B", "JPM", "UNH"],
    "AI_SOFTWARE":   ["MSFT", "GOOGL", "GOOG", "CRM", "NOW", "PLTR", "AI",
                      "SNOW", "ADBE", "ORCL", "BBAI", "PATH"],
    "CONSUMER_DIS":  ["AMZN", "TGT", "WMT", "COST", "HD", "LOW", "NKE",
                      "ELF", "CELH", "EL", "WYNN", "CAKE"],
}

SIZE_SCORE_SCALE = 700.0

CONC_BOOST_THRESHOLDS = [
    (0.15, 30.0),
    (0.10, 20.0),
    (0.05, 10.0),
]
CONC_FLOOR_WEIGHT = 0.01

CORR_RISK_THRESHOLDS = [
    (0.30, 10.0),
    (0.20,  5.0),
]

# ---------------------------------------------------------------------------
# Global Constants — Trim Score
# ---------------------------------------------------------------------------

TRIM_RISK_WEIGHT     = 0.50
TRIM_EXPOSURE_WEIGHT = 0.40
TRIM_STRENGTH_WEIGHT = 0.30

TRIM_GR1_STRENGTH_MIN = 80.0
TRIM_GR1_RISK_MAX     = 60.0
TRIM_GR1_EXPOSURE_MAX = 85.0
TRIM_GR1_CAP          = 55.0

# ---------------------------------------------------------------------------
# Global Constants — Upside Score (UV)
# ---------------------------------------------------------------------------

UV_WEIGHTS = {
    "distance_from_high":    0.30,
    "rsi_recovery":          0.25,
    "base_formation":        0.25,
    "rel_weakness_reversal": 0.20,
}

DIST_HIGH_LOOKBACK = 60
DIST_HIGH_SCALE    = 500.0   # 20% drawdown → 100

BASE_FORM_LOOKBACK    = 20
BASE_FORM_TIGHT_RANGE = 0.02  # range ≤ 2% → 100
BASE_FORM_LOOSE_RANGE = 0.12  # range ≥ 12% → 0

RWR_SCALE          = 2000.0
RWR_REVERSAL_BONUS = 25.0

# ---------------------------------------------------------------------------
# Global Constants — Recovery Confidence (RC)
# ---------------------------------------------------------------------------

RC_WEIGHTS = {
    "stability":       0.30,
    "vol_compression": 0.25,
    "trend_bottoming": 0.25,
    "volume_support":  0.20,
}

VOL_COMP_SHORT_WINDOW = 5    # recent ATR window
VOL_COMP_LONG_WINDOW  = 14   # baseline ATR window
VOL_COMP_OPT_RATIO    = 0.5  # ratio → score 100
VOL_COMP_MAX_RATIO    = 1.5  # ratio → score 0

# TrendBottoming: optimal = slight dip below MA20
BOTTOMING_LOWER = -0.20   # d20 < -20% → score 0 (too far below)
BOTTOMING_OPT   = -0.02   # ideal: just below MA20
BOTTOMING_UPPER =  0.10   # d20 > +10% → score 0 (already above)

VOL_SUPPORT_LOOKBACK = 15

# ---------------------------------------------------------------------------
# Global Constants — Setup Integrity Score (SIS)
# ---------------------------------------------------------------------------

SIS_BROKEN_TREND_POS_MAX   = 10.0   # trend_pos < this = broken
SIS_BROKEN_TREND_STR_MAX   = 20.0   # trend_struct < this = broken
SIS_BROKEN_TREND_PENALTY   = 50.0

SIS_HIGH_VOL_RATIO_FLOOR   = 1.30   # vol_ratio above this → penalty
SIS_HIGH_VOL_PENALTY_MAX   = 30.0   # max vol penalty
SIS_HIGH_VOL_PENALTY_RANGE = 0.70   # ratio range from floor to max

SIS_FREEFALL_D20_THRESHOLD = -0.15  # d20 < -15% = freefall
SIS_FREEFALL_PENALTY       = 25.0

# ---------------------------------------------------------------------------
# Global Constants — Add Score
# ---------------------------------------------------------------------------

ADD_UV_WEIGHT  = 0.40
ADD_RC_WEIGHT  = 0.35
ADD_SIS_WEIGHT = 0.25

ADD_GR1_STRENGTH_MIN = 70.0   # strength > this → cap (already extended)
ADD_GR1_CAP          = 40.0
ADD_GR2_TREND_POS_MAX  = 10.0  # both breached → broken trend
ADD_GR2_TREND_STR_MAX  = 20.0
ADD_GR2_CAP            = 20.0


# ---------------------------------------------------------------------------
# Helper: hybrid percentile score
# ---------------------------------------------------------------------------

def hybrid_score(raw_abs: float, value: float, population: list) -> float:
    n = len(population)
    if n < 8:
        alpha = HYBRID_ALPHA_N_LT_8
    elif n <= 14:
        alpha = HYBRID_ALPHA_N_8_TO_14
    else:
        alpha = HYBRID_ALPHA_N_GTE_15

    if alpha == 0.0:
        return raw_abs

    pct = percentile_rank(value, population) * 100.0
    return alpha * pct + (1.0 - alpha) * raw_abs


# ---------------------------------------------------------------------------
# Strength Score Components
# ---------------------------------------------------------------------------

def compute_rel_perf(close: list, spy_close: list, all_alpha_30d: list) -> dict:
    n_stock = len(close)
    n_spy   = len(spy_close)

    if n_stock < 31 or n_spy < 31:
        return {
            "score": FALLBACK_NEUTRAL,
            "alpha_30d": None,
            "stock_30d": None,
            "spy_30d": None,
            "fallback": True,
            "fallback_reason": "insufficient_history",
        }

    stock_30d = (close[0] - close[30]) / close[30]
    spy_30d   = (spy_close[0] - spy_close[30]) / spy_close[30]
    alpha_30d = stock_30d - spy_30d

    abs_score = clamp((alpha_30d - REL_PERF_ABS_MIN) / REL_PERF_ABS_RANGE * 100.0, 0.0, 100.0)
    score = hybrid_score(abs_score, alpha_30d, all_alpha_30d)

    return {
        "score": clamp(score, 0.0, 100.0),
        "alpha_30d": alpha_30d,
        "stock_30d": stock_30d,
        "spy_30d": spy_30d,
        "abs_score": abs_score,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_trend_pos(close: list) -> dict:
    n = len(close)

    if n < MIN_HISTORY_MA20:
        return {
            "score": FALLBACK_NEUTRAL,
            "fallback": True,
            "fallback_reason": "insufficient_history_ma20",
        }

    ma20 = compute_sma(close, 20)
    if ma20 is None or ma20 <= 0:
        return {
            "score": FALLBACK_NEUTRAL,
            "fallback": True,
            "fallback_reason": "ma20_zero_or_none",
        }

    d20 = (close[0] - ma20) / ma20
    s_20 = clamp((d20 / TREND_POS_S20_DENOM) * TREND_POS_SCALE + TREND_POS_OFFSET, 0.0, 100.0)

    ext_penalty = 0.0
    if d20 > TREND_POS_EXT_THRESHOLD:
        ext_penalty = clamp((d20 - TREND_POS_EXT_THRESHOLD) * TREND_POS_EXT_SCALE, 0.0, TREND_POS_EXT_PENALTY_CAP)

    ma50_fallback = False
    ma50_fallback_reason = None

    if n < MIN_HISTORY_MA50:
        ma50_fallback = True
        ma50_fallback_reason = "insufficient_history_ma50"
    else:
        ma50 = compute_sma(close, 50)
        if ma50 is None or ma50 <= 0:
            ma50_fallback = True
            ma50_fallback_reason = "ma50_zero_or_none"

    if ma50_fallback:
        score = clamp(s_20 - ext_penalty, 0.0, 100.0)
        return {
            "score": score,
            "d20": d20,
            "s_20": s_20,
            "s_stack": None,
            "base": s_20,
            "ext_penalty": ext_penalty,
            "fallback": True,
            "fallback_reason": ma50_fallback_reason,
        }

    ma50 = compute_sma(close, 50)
    stack_ratio = (ma20 - ma50) / ma50
    s_stack = clamp((stack_ratio / TREND_POS_STACK_DENOM) * TREND_POS_SCALE + TREND_POS_OFFSET, 0.0, 100.0)
    base  = TREND_POS_S20_WEIGHT * s_20 + TREND_POS_STACK_WEIGHT * s_stack
    score = clamp(base - ext_penalty, 0.0, 100.0)

    return {
        "score": score,
        "d20": d20,
        "s_20": s_20,
        "s_stack": s_stack,
        "stack_ratio": stack_ratio,
        "base": base,
        "ext_penalty": ext_penalty,
        "ma20": ma20,
        "ma50": ma50,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_trend_struct(close: list, all_slope_50: list) -> dict:
    n = len(close)

    if n < MIN_HISTORY_FULL:
        return {
            "score": FALLBACK_NEUTRAL,
            "slope_50": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_full_70",
        }

    ma50_now = compute_sma(close[0:],  50)
    ma50_t20 = compute_sma(close[20:], 50)

    if ma50_now is None or ma50_t20 is None or ma50_t20 <= 0:
        return {
            "score": FALLBACK_NEUTRAL,
            "slope_50": None,
            "fallback": True,
            "fallback_reason": "ma50_calculation_failed",
        }

    slope_50  = (ma50_now - ma50_t20) / ma50_t20
    abs_score = clamp(
        (slope_50 - TREND_STRUCT_ABS_MIN) / TREND_STRUCT_ABS_RANGE * 100.0,
        0.0, 100.0
    )
    score = hybrid_score(abs_score, slope_50, all_slope_50)

    return {
        "score": clamp(score, 0.0, 100.0),
        "slope_50": slope_50,
        "ma50_now": ma50_now,
        "ma50_t20": ma50_t20,
        "abs_score": abs_score,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_vol_conf(close: list, volume: list) -> dict:
    n = len(close)

    if n < 30:
        return {
            "score": FALLBACK_NEUTRAL,
            "up_days_vol": None,
            "down_days_vol": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_30",
        }

    lookback = min(VOL_CONF_LOOKBACK, n - 1)
    up_vols, down_vols = [], []
    for i in range(lookback):
        if i + 1 >= n:
            break
        change = close[i] - close[i + 1]
        if change > 0:
            up_vols.append(volume[i])
        elif change < 0:
            down_vols.append(volume[i])

    up_days_vol   = sum(up_vols)   / len(up_vols)   if up_vols   else 0.0
    down_days_vol = sum(down_vols) / len(down_vols) if down_vols else 0.0

    if up_days_vol + down_days_vol == 0.0:
        score = 50.0
    elif up_days_vol == 0.0:
        score = 0.0
    elif down_days_vol == 0.0:
        score = 100.0
    else:
        score = clamp(up_days_vol / (up_days_vol + down_days_vol) * 100.0, 0.0, 100.0)

    return {
        "score": score,
        "up_days_vol": up_days_vol,
        "down_days_vol": down_days_vol,
        "up_day_count": len(up_vols),
        "down_day_count": len(down_vols),
        "fallback": False,
        "fallback_reason": None,
    }


def compute_stability(high: list, low: list, close: list) -> dict:
    n = len(close)

    if n < 20:
        return {
            "score": FALLBACK_NEUTRAL,
            "atr_current": None,
            "atr_baseline": None,
            "vol_ratio": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_20",
        }

    atr_current = compute_atr(high, low, close, 0, STABILITY_ATR_CURRENT_PERIOD)

    if n < 43:
        baseline_start = STABILITY_ATR_CURRENT_PERIOD
        baseline_end   = n - 1
        if baseline_end <= baseline_start:
            return {
                "score": FALLBACK_NEUTRAL,
                "atr_current": atr_current,
                "atr_baseline": None,
                "vol_ratio": None,
                "fallback": True,
                "fallback_reason": "insufficient_history_43_partial",
            }
        atr_baseline = compute_atr(high, low, close, baseline_start, baseline_end)
        fallback = True
        fallback_reason = "baseline_window_shortened"
    else:
        atr_baseline = compute_atr(
            high, low, close,
            STABILITY_ATR_BASELINE_START,
            STABILITY_ATR_BASELINE_START + STABILITY_ATR_BASELINE_PERIOD
        )
        fallback = False
        fallback_reason = None

    if atr_baseline <= 0.0:
        return {
            "score": FALLBACK_NEUTRAL,
            "atr_current": atr_current,
            "atr_baseline": atr_baseline,
            "vol_ratio": None,
            "fallback": True,
            "fallback_reason": "atr_baseline_zero",
        }

    vol_ratio = atr_current / atr_baseline
    abs_score = clamp((2.0 - vol_ratio) / 1.5 * 100.0, 0.0, 100.0)

    return {
        "score": abs_score,
        "atr_current": atr_current,
        "atr_baseline": atr_baseline,
        "vol_ratio": vol_ratio,
        "fallback": fallback,
        "fallback_reason": fallback_reason,
    }


def compute_strength_score(
    rel_perf: float, trend_pos: float, trend_struct: float,
    vol_conf: float, stability: float,
) -> float:
    raw = (
        STRENGTH_WEIGHTS["rel_perf"]     * rel_perf
        + STRENGTH_WEIGHTS["trend_pos"]    * trend_pos
        + STRENGTH_WEIGHTS["trend_struct"] * trend_struct
        + STRENGTH_WEIGHTS["vol_conf"]     * vol_conf
        + STRENGTH_WEIGHTS["stability"]    * stability
    )
    return clamp(raw, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Risk Score Components
# ---------------------------------------------------------------------------

def compute_overext(close: list) -> dict:
    n = len(close)

    if n < MIN_HISTORY_MA20:
        return {
            "score": FALLBACK_NEUTRAL,
            "d20": None,
            "ma20": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_20",
        }

    ma20 = compute_sma(close, 20)
    if ma20 is None or ma20 <= 0:
        return {
            "score": FALLBACK_NEUTRAL,
            "d20": None,
            "ma20": ma20,
            "fallback": True,
            "fallback_reason": "ma20_zero_or_none",
        }

    d20   = (close[0] - ma20) / ma20
    score = clamp(d20 * OVEREXT_SCALE, 0.0, 100.0)

    return {
        "score": score,
        "d20": d20,
        "ma20": ma20,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_rsi_stretch(close: list) -> dict:
    rsi = compute_wilder_rsi(close, 14)

    if rsi < 50.0:
        score = 0.0
    elif rsi < 70.0:
        score = (rsi - 50.0) * 2.5
    else:
        score = 50.0 + (rsi - 70.0) * 5.0

    return {
        "score": clamp(score, 0.0, 100.0),
        "rsi": rsi,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_event_risk(days_to_earnings: Optional[int]) -> dict:
    if days_to_earnings is None or days_to_earnings < 0:
        score = EVENT_RISK_DEFAULT
        label = "unknown"
    else:
        score = EVENT_RISK_DEFAULT
        for threshold, threshold_score in EVENT_RISK_THRESHOLDS:
            if days_to_earnings <= threshold:
                score = threshold_score
                break
        label = str(days_to_earnings)

    return {
        "score": score,
        "days_to_earnings": days_to_earnings,
        "days_label": label,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_vol_exp(high: list, low: list, close: list) -> dict:
    n = len(close)

    if n < MIN_HISTORY_ATR14:
        return {
            "score": FALLBACK_NEUTRAL,
            "atr14": None,
            "atr50": None,
            "vol_ratio": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_15",
        }

    atr14 = compute_atr(high, low, close, 0, 14)

    if n < MIN_HISTORY_ATR50:
        baseline_end = n - 1
        if baseline_end <= 14:
            return {
                "score": FALLBACK_NEUTRAL,
                "atr14": atr14,
                "atr50": None,
                "vol_ratio": None,
                "fallback": True,
                "fallback_reason": "insufficient_history_51_no_baseline",
            }
        atr50 = compute_atr(high, low, close, 14, baseline_end)
        fallback = True
        fallback_reason = "atr50_window_shortened"
    else:
        atr50 = compute_atr(high, low, close, 0, 50)
        fallback = False
        fallback_reason = None

    if atr50 <= 0.0:
        return {
            "score": FALLBACK_NEUTRAL,
            "atr14": atr14,
            "atr50": atr50,
            "vol_ratio": None,
            "fallback": True,
            "fallback_reason": "atr50_zero",
        }

    vol_ratio = atr14 / atr50
    score     = clamp((vol_ratio - VOL_EXP_NEUTRAL_RATIO) * VOL_EXP_SCALE, 0.0, 100.0)

    return {
        "score": score,
        "atr14": atr14,
        "atr50": atr50,
        "vol_ratio": vol_ratio,
        "fallback": fallback,
        "fallback_reason": fallback_reason,
    }


def compute_accel(close: list) -> dict:
    n = len(close)

    if n < MIN_HISTORY_ACCEL:
        return {
            "score": 0.0,
            "r5": None,
            "r30": None,
            "accel_ratio": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_31",
        }

    if close[5] <= 0 or close[30] <= 0:
        return {
            "score": 0.0,
            "r5": None,
            "r30": None,
            "accel_ratio": None,
            "fallback": True,
            "fallback_reason": "zero_price_in_history",
        }

    r5  = (close[0] - close[5])  / close[5]
    r30 = (close[0] - close[30]) / close[30]

    daily_r5  = abs(r5)  / 5.0
    daily_r30 = abs(r30) / 30.0

    accel_ratio = daily_r5 / (daily_r30 + ACCEL_EPSILON)
    score       = clamp((accel_ratio - 1.0) * ACCEL_SCALE, 0.0, 100.0)

    return {
        "score": score,
        "r5": r5,
        "r30": r30,
        "daily_r5": daily_r5,
        "daily_r30": daily_r30,
        "accel_ratio": accel_ratio,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_gap_risk(open_: list, close: list) -> dict:
    n = len(close)

    if n < MIN_HISTORY_GAP_RISK:
        return {
            "score": 0.0,
            "gap_count": 0,
            "fallback": True,
            "fallback_reason": "insufficient_history_2",
        }

    lookback  = min(GAP_RISK_LOOKBACK, n - 1)
    gap_count = 0
    for i in range(lookback):
        prior_close = close[i + 1]
        if prior_close <= 0:
            continue
        gap_pct = abs(open_[i] - prior_close) / prior_close
        if gap_pct > GAP_RISK_THRESHOLD:
            gap_count += 1

    score = clamp(gap_count * GAP_RISK_PER_GAP, 0.0, 100.0)

    return {
        "score": score,
        "gap_count": gap_count,
        "lookback": lookback,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_risk_score(
    overext: float, rsi_stretch: float, event_risk: float,
    vol_exp: float, accel: float, gap_risk: float,
) -> float:
    raw = (
        RISK_WEIGHTS["overext"]     * overext
        + RISK_WEIGHTS["rsi_stretch"] * rsi_stretch
        + RISK_WEIGHTS["event_risk"]  * event_risk
        + RISK_WEIGHTS["vol_exp"]     * vol_exp
        + RISK_WEIGHTS["accel"]       * accel
        + RISK_WEIGHTS["gap_risk"]    * gap_risk
    )
    return clamp(raw, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Exposure Score Components
# ---------------------------------------------------------------------------

def compute_size_score(weight: float) -> dict:
    score = clamp(weight * SIZE_SCORE_SCALE, 0.0, 100.0)
    return {
        "score": score,
        "weight": weight,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_concentration_boost(weight: float) -> dict:
    if weight <= CONC_FLOOR_WEIGHT:
        boost = 0.0
    else:
        boost = 0.0
        for threshold, value in CONC_BOOST_THRESHOLDS:
            if weight > threshold:
                boost = value
                break

    return {
        "score": boost,
        "weight": weight,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_correlation_risk(ticker: str, all_weights: dict) -> dict:
    max_boost              = 0.0
    primary_cluster        = None
    primary_cluster_weight = 0.0
    cluster_detail         = {}

    for cluster_name, members in CLUSTERS.items():
        if ticker not in members:
            continue
        cluster_weight = sum(all_weights.get(m, 0.0) for m in members)

        boost = 0.0
        for threshold, value in CORR_RISK_THRESHOLDS:
            if cluster_weight > threshold:
                boost = value
                break

        cluster_detail[cluster_name] = {
            "cluster_weight": cluster_weight,
            "boost": boost,
        }

        if cluster_weight > primary_cluster_weight:
            primary_cluster_weight = cluster_weight
            primary_cluster        = cluster_name

        if boost > max_boost:
            max_boost = boost

    return {
        "score":                  max_boost,
        "primary_cluster":        primary_cluster,
        "primary_cluster_weight": primary_cluster_weight,
        "cluster_detail":         cluster_detail,
        "fallback":               False,
        "fallback_reason":        None,
    }


def compute_exposure_score(size_score: float, conc_boost: float, corr_risk: float) -> float:
    return clamp(size_score + conc_boost + corr_risk, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Trim Score
# ---------------------------------------------------------------------------

def compute_trim_score(strength: float, risk: float, exposure: float) -> dict:
    """
    Trim = (Risk × 0.5) + (Exposure × 0.4) − (Strength × 0.3)
    Guardrail 1: if S > 80 AND R < 60 AND E ≤ 85 → cap T at 55.
    Guardrail 2: clamp(raw, 0, 100) — T never negative.
    """
    raw   = TRIM_RISK_WEIGHT * risk + TRIM_EXPOSURE_WEIGHT * exposure - TRIM_STRENGTH_WEIGHT * strength
    score = clamp(raw, 0.0, 100.0)

    guardrail_1_applied = False
    if (strength > TRIM_GR1_STRENGTH_MIN
            and risk     < TRIM_GR1_RISK_MAX
            and exposure <= TRIM_GR1_EXPOSURE_MAX):
        score = min(score, TRIM_GR1_CAP)
        guardrail_1_applied = True

    return {
        "score":               round(score, 2),
        "raw":                 raw,
        "guardrail_1_applied": guardrail_1_applied,
        "inputs": {
            "strength": strength,
            "risk":     risk,
            "exposure": exposure,
        },
        "fallback":        False,
        "fallback_reason": None,
    }


# ---------------------------------------------------------------------------
# Upside Score (UV) Components
# ---------------------------------------------------------------------------

def compute_uv_distance_from_high(close: list, high: list) -> dict:
    """
    DistanceFromHigh — drawdown from the 60-day intraday high.

    drawdown = (peak_high - close[0]) / peak_high
    score = clamp(drawdown * 500, 0, 100)
    → 20% below peak → 100; at peak → 0.
    """
    n = len(close)
    if n < 5:
        return {
            "score": FALLBACK_NEUTRAL,
            "drawdown": None,
            "peak": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_5",
        }

    lookback = min(DIST_HIGH_LOOKBACK, n)
    peak = max(high[:lookback])
    if peak <= 0:
        return {
            "score": 0.0,
            "drawdown": None,
            "peak": peak,
            "fallback": True,
            "fallback_reason": "zero_peak",
        }

    drawdown = (peak - close[0]) / peak
    score    = clamp(drawdown * DIST_HIGH_SCALE, 0.0, 100.0)

    return {
        "score":    score,
        "drawdown": drawdown,
        "peak":     peak,
        "current":  close[0],
        "lookback": lookback,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_uv_rsi_recovery(close: list) -> dict:
    """
    RSIRecovery — RSI in the recovery zone scores highest.

    Piecewise linear, peak at RSI=40 (rebounding from oversold):
    RSI < 15:      0
    15 ≤ RSI < 25: 0 → 40
    25 ≤ RSI < 40: 40 → 100
    40 ≤ RSI < 55: 100 → 50
    55 ≤ RSI < 70: 50 → 0
    RSI ≥ 70:      0  (extended)
    """
    rsi = compute_wilder_rsi(close, 14)

    if rsi < 15.0:
        score = 0.0
    elif rsi < 25.0:
        score = (rsi - 15.0) / 10.0 * 40.0
    elif rsi < 40.0:
        score = 40.0 + (rsi - 25.0) / 15.0 * 60.0
    elif rsi < 55.0:
        score = 100.0 - (rsi - 40.0) / 15.0 * 50.0
    elif rsi < 70.0:
        score = 50.0 - (rsi - 55.0) / 15.0 * 50.0
    else:
        score = 0.0

    return {
        "score": clamp(score, 0.0, 100.0),
        "rsi":   rsi,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_uv_base_formation(close: list, high: list, low: list) -> dict:
    """
    BaseFormation — tight price range over 20 sessions = potential base.

    range_pct = (max_high - min_low) / min_low over last BASE_FORM_LOOKBACK bars
    score = clamp((LOOSE - range_pct) / (LOOSE - TIGHT) * 100, 0, 100)
    → range ≤ 2% → 100; range ≥ 12% → 0.
    """
    n = len(close)
    if n < BASE_FORM_LOOKBACK:
        return {
            "score": FALLBACK_NEUTRAL,
            "range_pct": None,
            "fallback": True,
            "fallback_reason": f"insufficient_history_{BASE_FORM_LOOKBACK}",
        }

    h_max = max(high[:BASE_FORM_LOOKBACK])
    l_min = min(low[:BASE_FORM_LOOKBACK])

    if l_min <= 0:
        return {
            "score": 0.0,
            "range_pct": None,
            "fallback": True,
            "fallback_reason": "zero_low",
        }

    range_pct = (h_max - l_min) / l_min
    score = clamp(
        (BASE_FORM_LOOSE_RANGE - range_pct) / (BASE_FORM_LOOSE_RANGE - BASE_FORM_TIGHT_RANGE) * 100.0,
        0.0, 100.0
    )

    return {
        "score":     score,
        "range_pct": range_pct,
        "h_max":     h_max,
        "l_min":     l_min,
        "fallback":  False,
        "fallback_reason": None,
    }


def compute_uv_rel_weakness_reversal(close: list, spy_close: list) -> dict:
    """
    RelativeWeaknessReversal — per Phase 1 spec (RelPerfImproving).

    improvement = alpha_5d - (alpha_30d / 6)
    base_score  = clamp(improvement * 2000, 0, 100)
    reversal_bonus = 25 if alpha_5d > 0 AND alpha_30d < 0 else 0

    Captures: stock was underperforming (alpha_30d < 0) but recent 5d
    outperformance is outpacing the 30d average daily drag.
    """
    n     = len(close)
    n_spy = len(spy_close)

    if n < 31 or n_spy < 31 or n < 6 or n_spy < 6:
        return {
            "score": 0.0,
            "alpha_30d": None,
            "alpha_5d": None,
            "improvement": None,
            "reversal_bonus": 0.0,
            "fallback": True,
            "fallback_reason": "insufficient_history",
        }

    stock_30d = (close[0] - close[30]) / close[30]
    spy_30d   = (spy_close[0] - spy_close[30]) / spy_close[30]
    alpha_30d = stock_30d - spy_30d

    stock_5d  = (close[0] - close[5]) / close[5]
    spy_5d    = (spy_close[0] - spy_close[5]) / spy_close[5]
    alpha_5d  = stock_5d - spy_5d

    improvement    = alpha_5d - (alpha_30d / 6.0)
    base_score     = clamp(improvement * RWR_SCALE, 0.0, 100.0)
    reversal_bonus = RWR_REVERSAL_BONUS if (alpha_5d > 0.0 and alpha_30d < 0.0) else 0.0
    score          = clamp(base_score + reversal_bonus, 0.0, 100.0)

    return {
        "score":          score,
        "alpha_30d":      alpha_30d,
        "alpha_5d":       alpha_5d,
        "improvement":    improvement,
        "reversal_bonus": reversal_bonus,
        "fallback":       False,
        "fallback_reason": None,
    }


def compute_upside_score(
    distance_from_high: float,
    rsi_recovery: float,
    base_formation: float,
    rel_weakness_reversal: float,
) -> float:
    """UV = weighted sum of four components, clamped [0, 100]."""
    raw = (
        UV_WEIGHTS["distance_from_high"]    * distance_from_high
        + UV_WEIGHTS["rsi_recovery"]          * rsi_recovery
        + UV_WEIGHTS["base_formation"]        * base_formation
        + UV_WEIGHTS["rel_weakness_reversal"] * rel_weakness_reversal
    )
    return clamp(raw, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Recovery Confidence (RC) Components
# ---------------------------------------------------------------------------

def compute_rc_vol_compression(high: list, low: list, close: list) -> dict:
    """
    VolatilityCompression — short-term ATR vs longer-term ATR.

    atr_short = mean TR over bars [0, VOL_COMP_SHORT_WINDOW)
    atr_long  = mean TR over bars [0, VOL_COMP_LONG_WINDOW)
    ratio = atr_short / atr_long
    score = clamp((MAX - ratio) / (MAX - OPT) * 100, 0, 100)
    → ratio=0.5 → 100 (compressing); ratio=1.5 → 0 (expanding).
    """
    n = len(close)
    min_needed = VOL_COMP_LONG_WINDOW + 1

    if n < min_needed:
        return {
            "score": FALLBACK_NEUTRAL,
            "atr_short": None,
            "atr_long": None,
            "ratio": None,
            "fallback": True,
            "fallback_reason": f"insufficient_history_{min_needed}",
        }

    atr_short = compute_atr(high, low, close, 0, VOL_COMP_SHORT_WINDOW)
    atr_long  = compute_atr(high, low, close, 0, VOL_COMP_LONG_WINDOW)

    if atr_long <= 0.0:
        return {
            "score": FALLBACK_NEUTRAL,
            "atr_short": atr_short,
            "atr_long": atr_long,
            "ratio": None,
            "fallback": True,
            "fallback_reason": "atr_long_zero",
        }

    ratio = atr_short / atr_long
    score = clamp(
        (VOL_COMP_MAX_RATIO - ratio) / (VOL_COMP_MAX_RATIO - VOL_COMP_OPT_RATIO) * 100.0,
        0.0, 100.0
    )

    return {
        "score":     score,
        "atr_short": atr_short,
        "atr_long":  atr_long,
        "ratio":     ratio,
        "fallback":  False,
        "fallback_reason": None,
    }


def compute_rc_trend_bottoming(close: list) -> dict:
    """
    TrendBottoming — price within the bottoming window relative to MA20.

    d20 = (close[0] - MA20) / MA20
    Optimal at d20 = BOTTOMING_OPT (-2%): slight dip below MA20.
    score = 0 if d20 < BOTTOMING_LOWER or d20 > BOTTOMING_UPPER.
    Linear from LOWER→OPT (0→100) and OPT→UPPER (100→0).
    """
    n = len(close)
    if n < MIN_HISTORY_MA20:
        return {
            "score": FALLBACK_NEUTRAL,
            "d20": None,
            "ma20": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_20",
        }

    ma20 = compute_sma(close, 20)
    if ma20 is None or ma20 <= 0:
        return {
            "score": FALLBACK_NEUTRAL,
            "d20": None,
            "ma20": ma20,
            "fallback": True,
            "fallback_reason": "ma20_zero_or_none",
        }

    d20 = (close[0] - ma20) / ma20

    if d20 < BOTTOMING_LOWER or d20 > BOTTOMING_UPPER:
        score = 0.0
    elif d20 <= BOTTOMING_OPT:
        score = clamp(
            (d20 - BOTTOMING_LOWER) / (BOTTOMING_OPT - BOTTOMING_LOWER) * 100.0,
            0.0, 100.0
        )
    else:
        score = clamp(
            100.0 - (d20 - BOTTOMING_OPT) / (BOTTOMING_UPPER - BOTTOMING_OPT) * 100.0,
            0.0, 100.0
        )

    return {
        "score": score,
        "d20":   d20,
        "ma20":  ma20,
        "fallback": False,
        "fallback_reason": None,
    }


def compute_rc_volume_support(close: list, volume: list) -> dict:
    """
    VolumeSupport — up-day volume vs average volume over the last 15 sessions.

    ratio = avg_up_day_vol / avg_all_day_vol
    score = clamp((ratio - 0.5) / 1.0 * 100, 0, 100)
    → ratio=1.5 → 100; ratio=0.5 → 0; ratio=1.0 → 50.
    """
    n = len(close)
    if n < 5:
        return {
            "score": FALLBACK_NEUTRAL,
            "ratio": None,
            "fallback": True,
            "fallback_reason": "insufficient_history_5",
        }

    lookback = min(VOL_SUPPORT_LOOKBACK, n - 1)
    up_vols, all_vols = [], []
    for i in range(lookback):
        if i + 1 >= n:
            break
        all_vols.append(volume[i])
        if close[i] > close[i + 1]:
            up_vols.append(volume[i])

    if not all_vols:
        return {
            "score": FALLBACK_NEUTRAL,
            "ratio": None,
            "fallback": True,
            "fallback_reason": "no_data",
        }

    avg_all = sum(all_vols) / len(all_vols)
    avg_up  = sum(up_vols)  / len(up_vols) if up_vols else 0.0

    if avg_all <= 0:
        return {
            "score": FALLBACK_NEUTRAL,
            "ratio": None,
            "fallback": True,
            "fallback_reason": "zero_avg_volume",
        }

    ratio = avg_up / avg_all
    score = clamp((ratio - 0.5) / 1.0 * 100.0, 0.0, 100.0)

    return {
        "score":        score,
        "ratio":        ratio,
        "avg_up_vol":   avg_up,
        "avg_all_vol":  avg_all,
        "up_day_count": len(up_vols),
        "fallback":     False,
        "fallback_reason": None,
    }


def compute_recovery_score(
    stability: float,
    vol_compression: float,
    trend_bottoming: float,
    volume_support: float,
) -> float:
    """RC = weighted sum of four components, clamped [0, 100]."""
    raw = (
        RC_WEIGHTS["stability"]       * stability
        + RC_WEIGHTS["vol_compression"] * vol_compression
        + RC_WEIGHTS["trend_bottoming"] * trend_bottoming
        + RC_WEIGHTS["volume_support"]  * volume_support
    )
    return clamp(raw, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Setup Integrity Score (SIS)
# ---------------------------------------------------------------------------

def compute_setup_integrity(
    trend_pos:    float,
    trend_struct: float,
    vol_ratio:    Optional[float],
    d20:          Optional[float],
) -> dict:
    """
    SIS starts at 100 and subtracts structural penalties.

    Penalty 1 — Broken trend (both MA dimensions broken):
        trend_pos < 10 AND trend_struct < 20 → -50

    Penalty 2 — Elevated volatility (ATR expanding):
        vol_ratio > 1.30: penalty = clamp((ratio-1.30)/0.70 * 30, 0, 30)

    Penalty 3 — Freefall (price severely extended below MA20):
        d20 < -15% → -25
    """
    penalties = {}

    if trend_pos < SIS_BROKEN_TREND_POS_MAX and trend_struct < SIS_BROKEN_TREND_STR_MAX:
        penalties["broken_trend"] = SIS_BROKEN_TREND_PENALTY
    else:
        penalties["broken_trend"] = 0.0

    if vol_ratio is not None and vol_ratio > SIS_HIGH_VOL_RATIO_FLOOR:
        vol_penalty = clamp(
            (vol_ratio - SIS_HIGH_VOL_RATIO_FLOOR) / SIS_HIGH_VOL_PENALTY_RANGE * SIS_HIGH_VOL_PENALTY_MAX,
            0.0, SIS_HIGH_VOL_PENALTY_MAX
        )
        penalties["high_volatility"] = vol_penalty
    else:
        penalties["high_volatility"] = 0.0

    if d20 is not None and d20 < SIS_FREEFALL_D20_THRESHOLD:
        penalties["freefall"] = SIS_FREEFALL_PENALTY
    else:
        penalties["freefall"] = 0.0

    total_penalty = sum(penalties.values())
    score         = clamp(100.0 - total_penalty, 0.0, 100.0)

    return {
        "score":         score,
        "penalties":     penalties,
        "total_penalty": total_penalty,
        "fallback":      False,
        "fallback_reason": None,
    }


# ---------------------------------------------------------------------------
# Add Score
# ---------------------------------------------------------------------------

def compute_add_score(
    uv:           float,
    rc:           float,
    sis:          float,
    strength:     float,
    trend_pos:    float,
    trend_struct: float,
) -> dict:
    """
    Add = UV×0.40 + RC×0.35 + SIS×0.25

    Guardrail 1: if Strength > 70 → cap Add at 40 (position already extended).
    Guardrail 2: if TrendPos < 10 AND TrendStruct < 20 → cap Add at 20 (broken trend).

    Guardrail 2 takes precedence over Guardrail 1 when both apply.
    """
    raw   = ADD_UV_WEIGHT * uv + ADD_RC_WEIGHT * rc + ADD_SIS_WEIGHT * sis
    score = clamp(raw, 0.0, 100.0)

    guardrail_1_applied = False
    guardrail_2_applied = False

    if strength > ADD_GR1_STRENGTH_MIN:
        score = min(score, ADD_GR1_CAP)
        guardrail_1_applied = True

    if trend_pos < ADD_GR2_TREND_POS_MAX and trend_struct < ADD_GR2_TREND_STR_MAX:
        score = min(score, ADD_GR2_CAP)
        guardrail_2_applied = True

    return {
        "score":               round(score, 2),
        "raw":                 raw,
        "guardrail_1_applied": guardrail_1_applied,
        "guardrail_2_applied": guardrail_2_applied,
        "inputs": {
            "uv":       uv,
            "rc":       rc,
            "sis":      sis,
            "strength": strength,
        },
        "fallback":        False,
        "fallback_reason": None,
    }
