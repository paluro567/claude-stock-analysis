"""
add_explanation.py — Natural-language explanation engine for the Add Score.

Mirrors explanation.py structure but targets the UV / RC / SIS / Add framework.

Called after compute_add_score. Returns a structured dict or None if add_score
is below ADD_EXPLANATION_THRESHOLD.
"""

from typing import Optional

ADD_EXPLANATION_THRESHOLD = 15.0  # surface explanations for add_score >= 15


# ---------------------------------------------------------------------------
# Action label
# ---------------------------------------------------------------------------

def _action_label(
    add_score:   float,
    sis_score:   float,
    guardrail_1: bool,
    guardrail_2: bool,
) -> str:
    """
    Avoid:               add < 25  OR  guardrail_2 applied  OR  SIS < 30
    High Conviction Add: add >= 65 AND SIS >= 60
    Watchlist:           add >= 40
    Monitor:             add >= 25
    """
    if add_score < 25.0 or guardrail_2 or sis_score < 30.0:
        return "Avoid"
    if add_score >= 65.0 and sis_score >= 60.0:
        return "High Conviction Add"
    if add_score >= 40.0:
        return "Watchlist"
    return "Monitor"


# ---------------------------------------------------------------------------
# Primary driver
# ---------------------------------------------------------------------------

def _primary_driver(
    uv_score:    float,
    rc_score:    float,
    sis_score:   float,
    guardrail_2: bool,
) -> str:
    """
    sis_constrained: guardrail_2 applied OR SIS < 50
    uv_dominant:     UV >= 40 AND UV > RC + 15
    rc_dominant:     RC >= 40 AND RC > UV + 15
    mixed:           default
    """
    if guardrail_2 or sis_score < 50.0:
        return "sis_constrained"
    if uv_score >= 40.0 and uv_score > rc_score + 15.0:
        return "uv_dominant"
    if rc_score >= 40.0 and rc_score > uv_score + 15.0:
        return "rc_dominant"
    return "mixed"


# ---------------------------------------------------------------------------
# Opportunity type
# ---------------------------------------------------------------------------

def _opportunity_type(
    add_score:    float,
    strength:     float,
    trend_struct: float,
    uv_comps:     dict,
    rc_comps:     dict,
    guardrail_1:  bool,
    guardrail_2:  bool,
) -> str:
    """
    broken_trend_avoid:  guardrail_2 applied (broken trend cap)
    extended_avoid:      guardrail_1 applied (strength already extended)
    pullback_in_uptrend: strength > 50 AND trend_struct > 40 AND drawdown > 5%
    reversal_candidate:  reversal_bonus > 0 (was underperforming, now bouncing)
    base_breakout:       base_formation score > 60
    oversold_bounce:     RSI < 35 AND strength < 40
    mixed:               default
    """
    if guardrail_2:
        return "broken_trend_avoid"
    if guardrail_1:
        return "extended_avoid"

    dfh      = uv_comps.get("distance_from_high", {})
    rsi_r    = uv_comps.get("rsi_recovery",       {})
    base     = uv_comps.get("base_formation",      {})
    rwr      = uv_comps.get("rel_weakness_reversal", {})

    drawdown     = dfh.get("drawdown") or 0.0
    base_score   = base.get("score", 0.0)
    rwr_bonus    = rwr.get("reversal_bonus", 0.0)
    rsi_val      = rsi_r.get("rsi", 50.0)

    if strength > 50.0 and trend_struct > 40.0 and drawdown > 0.05:
        return "pullback_in_uptrend"
    if rwr_bonus > 0.0:
        return "reversal_candidate"
    if base_score > 60.0:
        return "base_breakout"
    if rsi_val < 35.0 and strength < 40.0:
        return "oversold_bounce"
    return "mixed"


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

def _confidence(
    add_score:     float,
    sis_score:     float,
    dq_level:      str,
    all_fallbacks: list,
) -> str:
    """
    low:    suspended/provisional data OR SIS < 30 OR key UV/RC fallbacks present
    high:   no fallbacks AND SIS >= 60 AND add_score >= 40
    medium: default
    """
    key_fallbacks = {
        "distance_from_high", "rsi_recovery", "base_formation",
        "rel_weakness_reversal", "vol_compression", "trend_bottoming",
    }
    has_major_fallback = any(f in key_fallbacks for f in all_fallbacks)

    if dq_level in ("suspended", "provisional") or sis_score < 30.0 or has_major_fallback:
        return "low"
    if not all_fallbacks and sis_score >= 60.0 and add_score >= 40.0:
        return "high"
    return "medium"


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------

def _narrative(
    opportunity_type: str,
    uv_score:  float,
    rc_score:  float,
    sis_score: float,
    uv_comps:  dict,
    rc_comps:  dict,
    strength:  float,
    guardrail_1: bool,
    guardrail_2: bool,
) -> str:
    dfh   = uv_comps.get("distance_from_high",    {})
    rsi_r = uv_comps.get("rsi_recovery",           {})
    base  = uv_comps.get("base_formation",          {})
    rwr   = uv_comps.get("rel_weakness_reversal",  {})
    vc    = rc_comps.get("vol_compression",         {})
    tb    = rc_comps.get("trend_bottoming",         {})

    drawdown  = dfh.get("drawdown")
    rsi_val   = rsi_r.get("rsi", 50.0)
    range_pct = base.get("range_pct")
    alpha_30d = rwr.get("alpha_30d")
    ratio     = vc.get("ratio")
    d20       = tb.get("d20")

    drawdown_s  = f"{drawdown * 100:.1f}" if drawdown is not None else "N/A"
    range_pct_s = f"{range_pct * 100:.1f}" if range_pct is not None else "N/A"
    alpha_30d_s = f"{alpha_30d * 100:.1f}" if alpha_30d is not None else "N/A"
    ratio_s     = f"{ratio:.2f}" if ratio is not None else "N/A"
    d20_s       = f"{d20 * 100:.1f}" if d20 is not None else "N/A"

    if opportunity_type == "broken_trend_avoid":
        return (
            "Both trend dimensions are broken (TrendPos and TrendStruct below thresholds). "
            "Add Score capped at 20 by Guardrail 2. Avoid adding until structural trend recovers."
        )
    if opportunity_type == "extended_avoid":
        return (
            f"Strength Score of {strength:.0f} indicates the position is already extended. "
            f"Guardrail 1 caps Add at 40. RSI at {rsi_val:.0f} — wait for a pullback before adding."
        )
    if opportunity_type == "pullback_in_uptrend":
        return (
            f"Price is {drawdown_s}% below the 60-day high with intact uptrend structure. "
            f"RSI at {rsi_val:.0f} is in recovery range. Recovery Confidence: {rc_score:.0f}. "
            f"Structured pullback in a healthy trend — favorable add opportunity."
        )
    if opportunity_type == "reversal_candidate":
        return (
            f"Stock underperformed SPY by {alpha_30d_s}% over 30 days but shows improving "
            f"5-day momentum (reversal signal triggered). RSI at {rsi_val:.0f}. "
            f"Reversal candidate — watch for follow-through volume confirmation."
        )
    if opportunity_type == "base_breakout":
        return (
            f"Price has been consolidating in a {range_pct_s}% range over 20 sessions "
            f"(base formation score: {base.get('score', 0.0):.0f}). "
            f"Vol compression ratio: {ratio_s} — volatility contracting. "
            f"Potential base breakout setup; await volume confirmation."
        )
    if opportunity_type == "oversold_bounce":
        return (
            f"RSI at {rsi_val:.0f} is in deep oversold territory. "
            f"Price is {drawdown_s}% below 60-day high. "
            f"Weak trend (Strength: {strength:.0f}) limits conviction. "
            f"Tactical oversold bounce only — not a structural add."
        )
    # mixed
    return (
        f"UV: {uv_score:.0f}, RC: {rc_score:.0f}, SIS: {sis_score:.0f}. "
        f"No single dominant setup driver identified. "
        f"Mixed signals — monitor for setup clarity before adding."
    )


# ---------------------------------------------------------------------------
# Invalidation conditions
# ---------------------------------------------------------------------------

def _invalidation_conditions(
    opportunity_type: str,
    uv_comps:  dict,
    rc_comps:  dict,
    sis_score: float,
    strength:  float,
) -> list:
    dfh   = uv_comps.get("distance_from_high", {})
    rsi_r = uv_comps.get("rsi_recovery",       {})
    tb    = rc_comps.get("trend_bottoming",     {})
    vc    = rc_comps.get("vol_compression",     {})

    rsi_val  = rsi_r.get("rsi", 50.0)
    drawdown = dfh.get("drawdown")
    d20      = tb.get("d20")
    ratio    = vc.get("ratio")

    drawdown_s = f"{drawdown * 100:.1f}%" if drawdown is not None else "current drawdown"
    d20_s      = f"{d20 * 100:.1f}%" if d20 is not None else "current d20"
    ratio_s    = f"{ratio:.2f}" if ratio is not None else "current ratio"

    if opportunity_type == "broken_trend_avoid":
        return [
            "TrendPos recovers above 10 and TrendStruct recovers above 20 simultaneously",
            "Price closes above MA20 for 3 consecutive sessions",
            "RSI recovers above 40, signaling end of the breakdown phase",
        ]
    if opportunity_type == "extended_avoid":
        return [
            f"Strength Score drops below 70 as momentum normalizes",
            f"RSI pulls back from current {rsi_val:.0f} to below 55",
            f"Price retraces 5–10%, providing a lower-risk entry point",
        ]
    if opportunity_type == "pullback_in_uptrend":
        return [
            f"Price closes below MA20 and d20 extends beyond {d20_s}",
            f"RSI drops below 30, signaling a deeper corrective phase",
            f"Drawdown extends beyond {drawdown_s} without a reversal signal",
        ]
    if opportunity_type == "reversal_candidate":
        return [
            "5-day alpha turns negative again, invalidating the momentum reversal",
            f"RSI fails to hold above {rsi_val:.0f} and retreats toward 25",
            "Price breaks below the 20-day low on elevated volume",
        ]
    if opportunity_type == "base_breakout":
        return [
            "Price breaks below the base range low with elevated volume (failed base)",
            f"Vol compression ratio expands above {ratio_s} (volatility re-expanding)",
            "MA50 slope turns negative while price is still in the base",
        ]
    if opportunity_type == "oversold_bounce":
        return [
            f"RSI fails to recover above 35 within 5 sessions",
            f"Strength Score remains below {strength:.0f} with no trend improvement",
            f"SIS drops further below {sis_score:.0f} on additional volatility expansion",
        ]
    # mixed
    return [
        "Add Score drops below 25 on next scoring cycle",
        f"SIS drops below {sis_score:.0f} — structural conditions deteriorate",
        "Any primary trend indicator (TrendPos or TrendStruct) turns negative",
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_add_explanation(
    add_score:     float,
    uv_score:      float,
    rc_score:      float,
    sis_score:     float,
    strength:      float,
    trend_pos:     float,
    trend_struct:  float,
    uv_comps:      dict,
    rc_comps:      dict,
    guardrail_1:   bool,
    guardrail_2:   bool,
    dq_level:      str,
    all_fallbacks: list,
) -> Optional[dict]:
    """
    Returns a structured add explanation dict, or None if add_score < threshold.

    Parameters
    ----------
    add_score     : final Add Score (post-guardrails)
    uv_score      : raw Upside Score
    rc_score      : raw Recovery Confidence score
    sis_score     : Setup Integrity Score
    strength      : Strength Score (for guardrail context)
    trend_pos     : TrendPos component score
    trend_struct  : TrendStruct component score
    uv_comps      : dict of UV component result dicts (keyed by component name)
    rc_comps      : dict of RC component result dicts (keyed by component name)
    guardrail_1   : True if Add GR1 (strength cap) was applied
    guardrail_2   : True if Add GR2 (broken-trend cap) was applied
    dq_level      : data quality level string
    all_fallbacks : list of fallback component names across UV and RC
    """
    if add_score < ADD_EXPLANATION_THRESHOLD:
        return None

    action   = _action_label(add_score, sis_score, guardrail_1, guardrail_2)
    driver   = _primary_driver(uv_score, rc_score, sis_score, guardrail_2)
    opp_type = _opportunity_type(
        add_score, strength, trend_struct, uv_comps, rc_comps, guardrail_1, guardrail_2,
    )
    conf     = _confidence(add_score, sis_score, dq_level, all_fallbacks)
    narr     = _narrative(
        opp_type, uv_score, rc_score, sis_score,
        uv_comps, rc_comps, strength, guardrail_1, guardrail_2,
    )
    inval    = _invalidation_conditions(opp_type, uv_comps, rc_comps, sis_score, strength)

    return {
        "action_label":            action,
        "primary_driver":          driver,
        "opportunity_type":        opp_type,
        "confidence":              conf,
        "narrative":               narr,
        "invalidation_conditions": inval,
    }
