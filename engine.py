"""
engine.py — Two-pass scoring orchestration: Strength, Risk, Exposure, Trim.

Pass 1: Compute indicators and portfolio-level context for all holdings.
Pass 2: Score each ticker using cross-portfolio percentile and weight context.

Input schema per holding:
    {
        "ticker":            str,
        "quantity":          float,
        "days_to_earnings":  int | None,   # None = unknown / far out
        "ohlcv": {
            "open":   [float, ...],   # descending, index 0 = today
            "high":   [float, ...],
            "low":    [float, ...],
            "close":  [float, ...],
            "volume": [float, ...],
        }
    }

spy_ohlcv: { "close": [float, ...] }  # descending

Output schema (full):
    {
        "ticker":           str,
        "as_of":            str,
        "data_quality":     { "level", "reason_code", "scoring_mode" },
        "data_quality_flag": str | None,
        "strength":         { "score", "components", "fallback_components" },
        "risk":             { "score", "components", "fallback_components" },
        "exposure":         { "score", "components", "fallback_components" },
        "trim":             { "score", "raw", "guardrail_1_applied", "inputs" },
        "trim_explanation": dict | None,
    }
"""

from datetime import date
from typing import Optional

from explanation import compute_trim_explanation
from add_explanation import compute_add_explanation

from formulas import (
    # Strength
    compute_rel_perf,
    compute_trend_pos,
    compute_trend_struct,
    compute_vol_conf,
    compute_stability,
    compute_strength_score,
    # Risk
    compute_overext,
    compute_rsi_stretch,
    compute_event_risk,
    compute_vol_exp,
    compute_accel,
    compute_gap_risk,
    compute_risk_score,
    # Exposure
    compute_size_score,
    compute_concentration_boost,
    compute_correlation_risk,
    compute_exposure_score,
    # Trim
    compute_trim_score,
    # Upside (UV)
    compute_uv_distance_from_high,
    compute_uv_rsi_recovery,
    compute_uv_base_formation,
    compute_uv_rel_weakness_reversal,
    compute_upside_score,
    # Recovery Confidence (RC)
    compute_rc_vol_compression,
    compute_rc_trend_bottoming,
    compute_rc_volume_support,
    compute_recovery_score,
    # Setup Integrity + Add
    compute_setup_integrity,
    compute_add_score,
    # Constants
    FALLBACK_NEUTRAL,
    MIN_HISTORY_MA20,
    MIN_HISTORY_MA50,
    MIN_HISTORY_FULL,
)


# ---------------------------------------------------------------------------
# Data quality helpers
# ---------------------------------------------------------------------------

def _dq_level(n: int) -> str:
    if n < MIN_HISTORY_MA20:
        return "suspended"
    if n < MIN_HISTORY_MA50:
        return "provisional"
    if n < MIN_HISTORY_FULL:
        return "warning"
    return "none"


def _scoring_mode(level: str) -> str:
    if level == "suspended":
        return "fallback_only"
    if level == "provisional":
        return "partial"
    return "full"


def _reason_code(n: int) -> Optional[str]:
    if n < MIN_HISTORY_MA20:
        return f"only_{n}_bars_need_20"
    if n < MIN_HISTORY_MA50:
        return f"only_{n}_bars_need_50"
    if n < MIN_HISTORY_FULL:
        return f"only_{n}_bars_need_70"
    return None


def _dq_flag(level: str) -> Optional[str]:
    return {
        "suspended":   "SCORING_SUSPENDED",
        "provisional": "SCORING_PROVISIONAL",
        "warning":     "PARTIAL_SCORING",
        "none":        None,
    }.get(level)


# ---------------------------------------------------------------------------
# Suspended output builder
# ---------------------------------------------------------------------------

def _suspended_output(
    ticker: str, dq_level: str, reason: str, dq_flag_val: Optional[str],
    weight: float, all_weights: dict,
) -> dict:
    neutral_tech = {"score": FALLBACK_NEUTRAL, "fallback": True, "fallback_reason": "scoring_suspended"}

    # Exposure and Trim still computed even when technical scoring is suspended
    ss  = compute_size_score(weight)
    cb  = compute_concentration_boost(weight)
    cr  = compute_correlation_risk(ticker, all_weights)
    exp_total = compute_exposure_score(ss["score"], cb["score"], cr["score"])
    trim      = compute_trim_score(FALLBACK_NEUTRAL, FALLBACK_NEUTRAL, exp_total)

    # Explanation: pass suspended neutral components so metrics are readable
    neutral_risk_comps = {
        "overext":     {"score": FALLBACK_NEUTRAL, "d20": None, "ma20": None},
        "rsi_stretch": {"score": FALLBACK_NEUTRAL, "rsi": 50.0},
        "event_risk":  {"score": FALLBACK_NEUTRAL, "days_to_earnings": None},
        "vol_exp":     {"score": FALLBACK_NEUTRAL, "vol_ratio": None},
        "gap_risk":    {"score": FALLBACK_NEUTRAL, "gap_count": 0, "lookback": 20},
        "accel":       {"score": FALLBACK_NEUTRAL},
    }
    neutral_str_comps = {
        "rel_perf":     {"score": FALLBACK_NEUTRAL, "alpha_30d": None},
        "trend_pos":    {"score": FALLBACK_NEUTRAL, "d20": None, "ma20": None},
        "trend_struct": {"score": FALLBACK_NEUTRAL, "slope_50": None},
        "vol_conf":     {"score": FALLBACK_NEUTRAL},
        "stability":    {"score": FALLBACK_NEUTRAL},
    }
    all_fb = (["rel_perf", "trend_pos", "trend_struct", "vol_conf", "stability"]
              + ["overext", "rsi_stretch", "event_risk", "vol_exp", "accel", "gap_risk"])
    trim_expl = compute_trim_explanation(
        trim["score"], FALLBACK_NEUTRAL, FALLBACK_NEUTRAL, exp_total,
        neutral_risk_comps, {"size_score": ss, "concentration_boost": cb, "correlation_risk": cr},
        neutral_str_comps, dq_level, all_fb,
    )

    # ---- UV / RC / SIS / Add — neutral for suspended tickers ----
    uv_n = {"score": FALLBACK_NEUTRAL, "fallback": True, "fallback_reason": "scoring_suspended"}
    rc_n = {"score": FALLBACK_NEUTRAL, "fallback": True, "fallback_reason": "scoring_suspended"}

    uv_comps_susp = {
        "distance_from_high":    {**uv_n, "drawdown": None, "peak": None},
        "rsi_recovery":          {**uv_n, "rsi": 50.0},
        "base_formation":        {**uv_n, "range_pct": None},
        "rel_weakness_reversal": {**uv_n, "alpha_30d": None, "alpha_5d": None, "reversal_bonus": 0.0},
    }
    rc_comps_susp = {
        "stability":       {**rc_n, "atr_current": None, "atr_baseline": None, "vol_ratio": None},
        "vol_compression": {**rc_n, "atr_short": None, "atr_long": None, "ratio": None},
        "trend_bottoming": {**rc_n, "d20": None, "ma20": None},
        "volume_support":  {**rc_n, "ratio": None},
    }
    sis_susp = {
        "score": FALLBACK_NEUTRAL,
        "penalties":     {"broken_trend": 0.0, "high_volatility": 0.0, "freefall": 0.0},
        "total_penalty": 0.0,
        "fallback": True,
        "fallback_reason": "scoring_suspended",
    }
    add_susp = compute_add_score(
        FALLBACK_NEUTRAL, FALLBACK_NEUTRAL, FALLBACK_NEUTRAL,
        FALLBACK_NEUTRAL, FALLBACK_NEUTRAL, FALLBACK_NEUTRAL,
    )
    susp_uv_fallbacks = list(uv_comps_susp.keys())
    susp_rc_fallbacks = list(rc_comps_susp.keys())
    add_expl_susp = compute_add_explanation(
        add_score    = add_susp["score"],
        uv_score     = FALLBACK_NEUTRAL,
        rc_score     = FALLBACK_NEUTRAL,
        sis_score    = FALLBACK_NEUTRAL,
        strength     = FALLBACK_NEUTRAL,
        trend_pos    = FALLBACK_NEUTRAL,
        trend_struct = FALLBACK_NEUTRAL,
        uv_comps     = uv_comps_susp,
        rc_comps     = rc_comps_susp,
        guardrail_1  = add_susp["guardrail_1_applied"],
        guardrail_2  = add_susp["guardrail_2_applied"],
        dq_level     = dq_level,
        all_fallbacks = susp_uv_fallbacks + susp_rc_fallbacks,
    )

    return {
        "ticker": ticker,
        "as_of":  date.today().isoformat(),
        "data_quality": {
            "level":        dq_level,
            "reason_code":  reason,
            "scoring_mode": "fallback_only",
        },
        "data_quality_flag": dq_flag_val,
        "strength": {
            "score": FALLBACK_NEUTRAL,
            "components": {k: dict(neutral_tech) for k in
                           ("rel_perf", "trend_pos", "trend_struct", "vol_conf", "stability")},
            "fallback_components": ["rel_perf", "trend_pos", "trend_struct", "vol_conf", "stability"],
        },
        "risk": {
            "score": FALLBACK_NEUTRAL,
            "components": {k: dict(neutral_tech) for k in
                           ("overext", "rsi_stretch", "event_risk", "vol_exp", "accel", "gap_risk")},
            "fallback_components": ["overext", "rsi_stretch", "event_risk", "vol_exp", "accel", "gap_risk"],
        },
        "exposure": {
            "score": round(exp_total, 2),
            "components": {
                "size_score":           _serialize_component(ss),
                "concentration_boost":  _serialize_component(cb),
                "correlation_risk":     _serialize_component(cr),
            },
            "fallback_components": [],
        },
        "trim": trim,
        "trim_explanation": trim_expl,
        "upside": {
            "score": FALLBACK_NEUTRAL,
            "components": {k: _serialize_component(v) for k, v in uv_comps_susp.items()},
            "fallback_components": susp_uv_fallbacks,
        },
        "recovery": {
            "score": FALLBACK_NEUTRAL,
            "components": {k: _serialize_component(v) for k, v in rc_comps_susp.items()},
            "fallback_components": susp_rc_fallbacks,
        },
        "setup_integrity": sis_susp,
        "add":             add_susp,
        "add_explanation": add_expl_susp,
    }


# ---------------------------------------------------------------------------
# Pass 1: Extract cross-portfolio indicators + position weights
# ---------------------------------------------------------------------------

def _extract_pass1_indicators(holding: dict, spy_close: list) -> dict:
    close = holding["ohlcv"]["close"]
    n     = len(close)
    n_spy = len(spy_close)
    qty   = holding.get("quantity", 0.0)

    position_value = close[0] * qty if close else 0.0

    result = {
        "ticker":         holding["ticker"],
        "n":              n,
        "dq_level":       _dq_level(n),
        "alpha_30d":      None,
        "slope_50":       None,
        "position_value": position_value,
        "weight":         0.0,   # filled after all values summed
    }

    if n >= 31 and n_spy >= 31:
        stock_30d = (close[0] - close[30]) / close[30]
        spy_30d   = (spy_close[0] - spy_close[30]) / spy_close[30]
        result["alpha_30d"] = stock_30d - spy_30d

    if n >= MIN_HISTORY_FULL:
        from indicators import compute_sma
        ma50_now = compute_sma(close[0:],  50)
        ma50_t20 = compute_sma(close[20:], 50)
        if ma50_now and ma50_t20 and ma50_t20 > 0:
            result["slope_50"] = (ma50_now - ma50_t20) / ma50_t20

    return result


# ---------------------------------------------------------------------------
# Component dict serializer (rounds floats, keeps all breakdown keys)
# ---------------------------------------------------------------------------

def _serialize_component(v: dict) -> dict:
    out = {}
    for kk, vv in v.items():
        if isinstance(vv, float):
            out[kk] = round(vv, 6)
        elif isinstance(vv, dict):
            # nested dict (e.g. cluster_detail) — serialize recursively
            out[kk] = {
                kkk: round(vvv, 6) if isinstance(vvv, float) else vvv
                for kkk, vvv in vv.items()
            }
        else:
            out[kk] = vv
    return out


# ---------------------------------------------------------------------------
# Pass 2: Score a single ticker
# ---------------------------------------------------------------------------

def _score_ticker(
    holding: dict,
    spy_close: list,
    all_alpha_30d: list,
    all_slope_50: list,
    weight: float,
    all_weights: dict,
) -> dict:
    ticker = holding["ticker"]
    ohlcv  = holding["ohlcv"]
    close  = ohlcv["close"]
    high   = ohlcv["high"]
    low    = ohlcv["low"]
    open_  = ohlcv["open"]
    volume = ohlcv["volume"]
    n      = len(close)

    days_to_earnings = holding.get("days_to_earnings", None)

    dq_level   = _dq_level(n)
    score_mode = _scoring_mode(dq_level)
    reason     = _reason_code(n)
    dq_flag_v  = _dq_flag(dq_level)

    if dq_level == "suspended":
        return _suspended_output(ticker, dq_level, reason, dq_flag_v, weight, all_weights)

    # ---- Strength components ----
    rp = compute_rel_perf(close, spy_close, all_alpha_30d)
    tp = compute_trend_pos(close)
    ts = compute_trend_struct(close, all_slope_50)
    vc = compute_vol_conf(close, volume)
    st = compute_stability(high, low, close)

    strength_components = {
        "rel_perf": rp, "trend_pos": tp, "trend_struct": ts,
        "vol_conf": vc, "stability": st,
    }
    strength_fallbacks = [k for k, v in strength_components.items() if v.get("fallback")]
    strength_total     = compute_strength_score(
        rp["score"], tp["score"], ts["score"], vc["score"], st["score"]
    )

    # ---- Risk components ----
    ox = compute_overext(close)
    rs = compute_rsi_stretch(close)
    er = compute_event_risk(days_to_earnings)
    ve = compute_vol_exp(high, low, close)
    ac = compute_accel(close)
    gr = compute_gap_risk(open_, close)

    risk_components = {
        "overext": ox, "rsi_stretch": rs, "event_risk": er,
        "vol_exp": ve, "accel": ac, "gap_risk": gr,
    }
    risk_fallbacks = [k for k, v in risk_components.items() if v.get("fallback")]
    risk_total     = compute_risk_score(
        ox["score"], rs["score"], er["score"], ve["score"], ac["score"], gr["score"]
    )

    # ---- Exposure components ----
    ss = compute_size_score(weight)
    cb = compute_concentration_boost(weight)
    cr = compute_correlation_risk(ticker, all_weights)

    exposure_components = {
        "size_score":          ss,
        "concentration_boost": cb,
        "correlation_risk":    cr,
    }
    exposure_fallbacks = [k for k, v in exposure_components.items() if v.get("fallback")]
    exposure_total     = compute_exposure_score(ss["score"], cb["score"], cr["score"])

    # ---- Trim Score ----
    trim = compute_trim_score(strength_total, risk_total, exposure_total)

    # ---- Trim Explanation ----
    all_fallbacks = strength_fallbacks + risk_fallbacks + exposure_fallbacks
    trim_expl = compute_trim_explanation(
        trim_score     = trim["score"],
        strength_score = strength_total,
        risk_score     = risk_total,
        exposure_score = exposure_total,
        risk_comps     = risk_components,
        exp_comps      = exposure_components,
        str_comps      = strength_components,
        dq_level       = dq_level,
        all_fallbacks  = all_fallbacks,
    )

    # ---- Upside Score (UV) components ----
    uv_dfh = compute_uv_distance_from_high(close, high)
    uv_rsi = compute_uv_rsi_recovery(close)
    uv_bf  = compute_uv_base_formation(close, high, low)
    uv_rwr = compute_uv_rel_weakness_reversal(close, spy_close)

    uv_components = {
        "distance_from_high":    uv_dfh,
        "rsi_recovery":          uv_rsi,
        "base_formation":        uv_bf,
        "rel_weakness_reversal": uv_rwr,
    }
    uv_fallbacks = [k for k, v in uv_components.items() if v.get("fallback")]
    uv_total = compute_upside_score(
        uv_dfh["score"], uv_rsi["score"], uv_bf["score"], uv_rwr["score"],
    )

    # ---- Recovery Confidence (RC) components ----
    # stability reused from Strength (st); d20 reused from overext (ox)
    rc_vc = compute_rc_vol_compression(high, low, close)
    rc_tb = compute_rc_trend_bottoming(close)
    rc_vs = compute_rc_volume_support(close, volume)

    rc_components = {
        "stability":       st,    # reused from Strength
        "vol_compression": rc_vc,
        "trend_bottoming": rc_tb,
        "volume_support":  rc_vs,
    }
    rc_fallbacks = [k for k, v in rc_components.items() if v.get("fallback")]
    rc_total = compute_recovery_score(
        st["score"], rc_vc["score"], rc_tb["score"], rc_vs["score"],
    )

    # ---- Setup Integrity Score (SIS) ----
    # d20 from overext; vol_ratio from vol_exp; trend scores from Strength
    sis = compute_setup_integrity(
        trend_pos    = tp["score"],
        trend_struct = ts["score"],
        vol_ratio    = ve.get("vol_ratio"),
        d20          = ox.get("d20"),
    )

    # ---- Add Score ----
    add = compute_add_score(
        uv           = uv_total,
        rc           = rc_total,
        sis          = sis["score"],
        strength     = strength_total,
        trend_pos    = tp["score"],
        trend_struct = ts["score"],
    )

    # ---- Add Explanation ----
    add_all_fallbacks = uv_fallbacks + rc_fallbacks
    add_expl = compute_add_explanation(
        add_score    = add["score"],
        uv_score     = uv_total,
        rc_score     = rc_total,
        sis_score    = sis["score"],
        strength     = strength_total,
        trend_pos    = tp["score"],
        trend_struct = ts["score"],
        uv_comps     = uv_components,
        rc_comps     = rc_components,
        guardrail_1  = add["guardrail_1_applied"],
        guardrail_2  = add["guardrail_2_applied"],
        dq_level     = dq_level,
        all_fallbacks = add_all_fallbacks,
    )

    return {
        "ticker": ticker,
        "as_of":  date.today().isoformat(),
        "data_quality": {
            "level":        dq_level,
            "reason_code":  reason,
            "scoring_mode": score_mode,
        },
        "data_quality_flag": dq_flag_v,
        "strength": {
            "score": round(strength_total, 2),
            "components": {k: _serialize_component(v) for k, v in strength_components.items()},
            "fallback_components": strength_fallbacks,
        },
        "risk": {
            "score": round(risk_total, 2),
            "components": {k: _serialize_component(v) for k, v in risk_components.items()},
            "fallback_components": risk_fallbacks,
        },
        "exposure": {
            "score": round(exposure_total, 2),
            "components": {k: _serialize_component(v) for k, v in exposure_components.items()},
            "fallback_components": exposure_fallbacks,
        },
        "trim": trim,
        "trim_explanation": trim_expl,
        "upside": {
            "score": round(uv_total, 2),
            "components": {k: _serialize_component(v) for k, v in uv_components.items()},
            "fallback_components": uv_fallbacks,
        },
        "recovery": {
            "score": round(rc_total, 2),
            "components": {k: _serialize_component(v) for k, v in rc_components.items()},
            "fallback_components": rc_fallbacks,
        },
        "setup_integrity": _serialize_component(sis),
        "add":             add,
        "add_explanation": add_expl,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_engine(holdings: list, spy_ohlcv: dict) -> list:
    """
    Two-pass scoring engine.

    holdings  : list of holding dicts (ticker, quantity, days_to_earnings, ohlcv)
    spy_ohlcv : dict with "close" key (descending list)

    Returns list of scored ticker dicts.
    """
    spy_close = spy_ohlcv["close"]

    # ---- PASS 1: build cross-portfolio populations and compute weights ----
    pass1 = [_extract_pass1_indicators(h, spy_close) for h in holdings]

    total_value = sum(p["position_value"] for p in pass1)
    if total_value > 0:
        for p in pass1:
            p["weight"] = p["position_value"] / total_value
    # else all weights remain 0.0

    all_weights   = {p["ticker"]: p["weight"] for p in pass1}
    all_alpha_30d = [p["alpha_30d"] for p in pass1 if p["alpha_30d"] is not None]
    all_slope_50  = [p["slope_50"]  for p in pass1 if p["slope_50"]  is not None]

    # ---- PASS 2: score each ticker ----
    results = []
    for holding, p1 in zip(holdings, pass1):
        result = _score_ticker(
            holding, spy_close, all_alpha_30d, all_slope_50,
            p1["weight"], all_weights,
        )
        results.append(result)

    return results
