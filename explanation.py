"""
explanation.py — Trim explanation engine.

Deterministic, rule-based. All narrative text uses actual computed metric values.
No AI-generated prose. No generic language.

Generates trim_explanation only when trim_score >= EXPLANATION_THRESHOLD.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Thresholds and constants
# ---------------------------------------------------------------------------

EXPLANATION_THRESHOLD            = 25.0   # below this → trim_explanation = None
ACTION_HIGH_PRIORITY_TRIM_MIN    = 70.0   # trim score floor for High Priority Trim
ACTION_HIGH_PRIORITY_RISK_MIN    = 70.0   # risk score requirement for High Priority Trim
ACTION_HIGH_PRIORITY_EXPOSURE_MIN= 80.0   # exposure score requirement for High Priority Trim
ACTION_PARTIAL_MIN               = 60.0   # trim score floor for Partial Trim / Extended labels

# Primary driver: exposure_contribution vs risk_contribution
DRIVER_RATIO                     = 1.10   # dominant side must exceed other * this
DRIVER_EXPOSURE_SCORE_MIN        = 50.0   # exposure_score floor for "exposure" driver
DRIVER_RISK_SCORE_MIN            = 30.0   # risk_score floor for "risk" driver

# Technical risk type signal thresholds
OVEREXT_SIGNAL_MIN               = 25.0   # combined overext+rsi+accel signal
EVENT_SIGNAL_MIN                 = 60.0   # event_risk score minimum
WEAK_TREND_SIGNAL_MIN            = 30.0   # combined trend weakness score
VOL_SIGNAL_MIN                   = 30.0   # combined volatility signal

# Exposure risk type thresholds
CONC_BOOST_RISK_TYPE_MIN         = 20.0   # conc_boost score → Concentration Risk
CORR_RISK_RISK_TYPE_MIN          = 5.0    # corr_risk score → Correlation Cluster Risk

# Dominance ratio for single-winner classification
DOMINANCE_RATIO                  = 1.5

# "Extended but Trend Intact" conditions
EXTENDED_STRENGTH_MIN            = 65.0   # strength must exceed this


# ---------------------------------------------------------------------------
# Primary driver classification
# ---------------------------------------------------------------------------

def _primary_driver(risk_score: float, exposure_score: float) -> str:
    """
    Classify what is driving the Trim score: risk-channel, exposure-channel, or both.

    risk_contribution    = risk_score * 0.5
    exposure_contribution = exposure_score * 0.4

    exposure:        exposure_contribution > risk * RATIO and exposure_score >= floor
    risk:            risk_contribution > exposure * RATIO and risk_score >= floor
    risk_and_exposure: otherwise
    """
    rc = risk_score     * 0.5
    ec = exposure_score * 0.4

    if ec > rc * DRIVER_RATIO and exposure_score >= DRIVER_EXPOSURE_SCORE_MIN:
        return "exposure"
    if rc > ec * DRIVER_RATIO and risk_score >= DRIVER_RISK_SCORE_MIN:
        return "risk"
    return "risk_and_exposure"


# ---------------------------------------------------------------------------
# Risk type classification — exposure channel
# ---------------------------------------------------------------------------

def _exposure_risk_type(exp_comps: dict) -> str:
    """
    When primary_driver == 'exposure': classify between Concentration and Cluster risk.
    Concentration Risk takes precedence when conc_boost crosses the large-position threshold.
    """
    conc_boost = exp_comps["concentration_boost"]["score"]
    corr_risk  = exp_comps["correlation_risk"]["score"]

    if conc_boost >= CONC_BOOST_RISK_TYPE_MIN:
        return "Concentration Risk"
    if corr_risk >= CORR_RISK_RISK_TYPE_MIN:
        return "Correlation Cluster Risk"
    return "Mixed Risk"


# ---------------------------------------------------------------------------
# Risk type classification — technical (risk) channel
# ---------------------------------------------------------------------------

def _technical_risk_type(risk_comps: dict, str_comps: dict) -> str:
    """
    When primary_driver == 'risk': classify among Overextension, Event,
    Weak Trend, Volatility, Mixed.
    """
    overext      = risk_comps["overext"]["score"]
    rsi_stretch  = risk_comps["rsi_stretch"]["score"]
    event_risk   = risk_comps["event_risk"]["score"]
    vol_exp      = risk_comps["vol_exp"]["score"]
    gap_risk     = risk_comps["gap_risk"]["score"]
    accel        = risk_comps["accel"]["score"]
    trend_pos    = str_comps["trend_pos"]["score"]
    trend_struct = str_comps["trend_struct"]["score"]

    candidates = {}

    # Overextension: price extension, RSI overbought, rapid acceleration
    overext_signal = overext * 0.40 + rsi_stretch * 0.30 + accel * 0.30
    if overext_signal >= OVEREXT_SIGNAL_MIN:
        candidates["Overextension Risk"] = overext_signal

    # Event Risk: near-term earnings
    if event_risk >= EVENT_SIGNAL_MIN:
        candidates["Event Risk"] = event_risk

    # Weak Trend Risk: price below or near MAs, MA50 declining
    trend_weakness = max(0.0, 50.0 - trend_pos) + max(0.0, 50.0 - trend_struct)
    if trend_weakness >= WEAK_TREND_SIGNAL_MIN:
        candidates["Weak Trend Risk"] = trend_weakness

    # Volatility Risk: ATR expansion or gap frequency
    vol_signal = max(
        vol_exp * 0.5 + gap_risk * 0.5,
        max(vol_exp, gap_risk) * 0.7,
    )
    if vol_signal >= VOL_SIGNAL_MIN:
        candidates["Volatility Risk"] = vol_signal

    if not candidates:
        return "Mixed Risk"
    if len(candidates) == 1:
        return next(iter(candidates))

    sorted_c = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    if sorted_c[0][1] >= sorted_c[1][1] * DOMINANCE_RATIO:
        return sorted_c[0][0]
    return "Mixed Risk"


# ---------------------------------------------------------------------------
# Risk type dispatcher
# ---------------------------------------------------------------------------

def _classify_risk_type(
    primary_driver: str,
    risk_comps: dict,
    exp_comps: dict,
    str_comps: dict,
) -> str:
    """
    Route risk type classification based on primary driver.

    exposure:         classify within exposure channel (Concentration / Cluster)
    risk:             classify within technical channel (Overext / Event / Weak Trend / Vol)
    risk_and_exposure: classify technical; fall back to exposure if technical is mixed
    """
    if primary_driver == "exposure":
        return _exposure_risk_type(exp_comps)

    if primary_driver == "risk":
        return _technical_risk_type(risk_comps, str_comps)

    # risk_and_exposure: use whichever channel has a clear classification
    tech_type = _technical_risk_type(risk_comps, str_comps)
    if tech_type != "Mixed Risk":
        return tech_type
    return _exposure_risk_type(exp_comps)


# ---------------------------------------------------------------------------
# Action label
# ---------------------------------------------------------------------------

def _action_label(
    trim_score: float,
    risk_score: float,
    exposure_score: float,
    strength_score: float,
    risk_type: str,
    risk_comps: dict,
) -> str:
    """
    High Priority Trim    : T ≥ 70 AND (R ≥ 70 OR E ≥ 80)
    Extended but Trend Intact: T ≥ 60 AND risk_type == Overextension Risk AND S > 65
    Partial Trim Candidate: T ≥ 60
    Monitor Only          : T >= EXPLANATION_THRESHOLD (below Partial)
    """
    if (trim_score >= ACTION_HIGH_PRIORITY_TRIM_MIN
            and (risk_score >= ACTION_HIGH_PRIORITY_RISK_MIN
                 or exposure_score >= ACTION_HIGH_PRIORITY_EXPOSURE_MIN)):
        return "High Priority Trim"

    if trim_score >= ACTION_PARTIAL_MIN:
        overext     = risk_comps["overext"]["score"]
        rsi_stretch = risk_comps["rsi_stretch"]["score"]
        accel       = risk_comps["accel"]["score"]
        overext_signal = overext * 0.40 + rsi_stretch * 0.30 + accel * 0.30
        if (risk_type == "Overextension Risk"
                and overext_signal >= OVEREXT_SIGNAL_MIN
                and strength_score > EXTENDED_STRENGTH_MIN):
            return "Extended but Trend Intact"
        return "Partial Trim Candidate"

    return "Monitor Only"


# ---------------------------------------------------------------------------
# Confidence level
# ---------------------------------------------------------------------------

def _confidence(
    dq_level: str,
    all_fallbacks: list,
    primary_driver: str,
    risk_type: str,
    trim_score: float,
) -> str:
    """
    high:   T ≥ 70, dq=none, no fallbacks, clear driver and risk_type
    medium: clear driver+type, ≤2 fallbacks, dq not provisional
    low:    provisional/suspended, >2 fallbacks, or mixed driver+type with fallbacks
    """
    if dq_level in ("suspended", "provisional"):
        return "low"

    n_fb = len(all_fallbacks)
    if n_fb > 2:
        return "low"

    is_mixed = (risk_type == "Mixed Risk" or primary_driver == "risk_and_exposure")

    if is_mixed and n_fb > 0:
        return "low"

    if trim_score >= ACTION_HIGH_PRIORITY_TRIM_MIN and not is_mixed and n_fb == 0 and dq_level == "none":
        return "high"

    return "medium"


# ---------------------------------------------------------------------------
# Narrative builder
# ---------------------------------------------------------------------------

def _extract_metrics(risk_comps: dict, exp_comps: dict, str_comps: dict) -> dict:
    """Extract all metric values used by narratives and invalidation conditions."""
    m = {}

    # Risk metrics
    m["overext"]      = risk_comps["overext"]["score"]
    m["d20"]          = risk_comps["overext"].get("d20") or 0.0
    m["ma20"]         = risk_comps["overext"].get("ma20") or 0.0
    m["rsi_stretch"]  = risk_comps["rsi_stretch"]["score"]
    m["rsi"]          = risk_comps["rsi_stretch"].get("rsi") or 50.0
    m["event_risk"]   = risk_comps["event_risk"]["score"]
    m["days"]         = risk_comps["event_risk"].get("days_to_earnings")
    m["vol_exp"]      = risk_comps["vol_exp"]["score"]
    m["vol_ratio"]    = risk_comps["vol_exp"].get("vol_ratio") or 1.0
    m["gap_risk"]     = risk_comps["gap_risk"]["score"]
    m["gaps"]         = risk_comps["gap_risk"].get("gap_count") or 0
    m["lookback"]     = risk_comps["gap_risk"].get("lookback") or 20
    m["accel"]        = risk_comps["accel"]["score"]

    # Exposure metrics
    m["size_score"]   = exp_comps["size_score"]["score"]
    m["weight"]       = (exp_comps["size_score"].get("weight") or 0.0) * 100.0
    m["conc_boost"]   = exp_comps["concentration_boost"]["score"]
    m["corr_risk"]    = exp_comps["correlation_risk"]["score"]
    m["cluster"]      = exp_comps["correlation_risk"].get("primary_cluster") or "none"
    m["cluster_wt"]   = (exp_comps["correlation_risk"].get("primary_cluster_weight") or 0.0) * 100.0

    # Strength metrics
    m["trend_pos"]    = str_comps["trend_pos"]["score"]
    m["trend_struct"] = str_comps["trend_struct"]["score"]
    m["slope_50"]     = (str_comps["trend_struct"].get("slope_50") or 0.0) * 100.0
    m["rel_perf"]     = str_comps["rel_perf"]["score"]
    m["alpha_30d"]    = (str_comps["rel_perf"].get("alpha_30d") or 0.0) * 100.0

    # Derived pct forms
    m["d20_pct"]      = m["d20"] * 100.0
    m["days_str"]     = str(m["days"]) if m["days"] is not None else "unknown"

    return m


def _narrative(
    risk_type: str,
    strength_score: float,
    risk_score: float,
    exposure_score: float,
    m: dict,
) -> str:
    if risk_type == "Overextension Risk":
        return (
            f"Overext={m['overext']:.1f}: price {m['d20_pct']:+.1f}% above "
            f"MA20={m['ma20']:.2f}. "
            f"RSI={m['rsi']:.1f} (RSIStretch={m['rsi_stretch']:.1f}). "
            f"Accel={m['accel']:.1f}. "
            f"Strength={strength_score:.1f}, TrendPos={m['trend_pos']:.1f}."
        )

    if risk_type == "Event Risk":
        return (
            f"EventRisk={m['event_risk']:.1f}: earnings in {m['days_str']} days. "
            f"Overext={m['overext']:.1f} (price {m['d20_pct']:+.1f}% vs MA20={m['ma20']:.2f}), "
            f"RSI={m['rsi']:.1f}. "
            f"Exposure={exposure_score:.1f}, Risk={risk_score:.1f}. "
            f"Strength={strength_score:.1f}."
        )

    if risk_type == "Concentration Risk":
        return (
            f"Exposure={exposure_score:.1f}: weight={m['weight']:.1f}%, "
            f"SizeScore={m['size_score']:.1f}, ConcBoost={m['conc_boost']:.1f}, "
            f"CorrRisk={m['corr_risk']:.1f} "
            f"(cluster {m['cluster']} at {m['cluster_wt']:.1f}%). "
            f"Risk={risk_score:.1f}. Strength={strength_score:.1f}."
        )

    if risk_type == "Correlation Cluster Risk":
        return (
            f"CorrRisk={m['corr_risk']:.1f}: cluster {m['cluster']} "
            f"at {m['cluster_wt']:.1f}% of portfolio. "
            f"Position weight={m['weight']:.1f}% (ConcBoost={m['conc_boost']:.1f}). "
            f"Exposure={exposure_score:.1f}, Risk={risk_score:.1f}."
        )

    if risk_type == "Weak Trend Risk":
        return (
            f"TrendPos={m['trend_pos']:.1f}, TrendStruct={m['trend_struct']:.1f}: "
            f"price {m['d20_pct']:+.1f}% vs MA20={m['ma20']:.2f}, "
            f"MA50 slope={m['slope_50']:.3f}%. "
            f"RelPerf={m['rel_perf']:.1f} (30d alpha {m['alpha_30d']:+.1f}%). "
            f"Strength={strength_score:.1f}."
        )

    if risk_type == "Volatility Risk":
        return (
            f"VolExp={m['vol_exp']:.1f} (ATR14/ATR50={m['vol_ratio']:.2f}), "
            f"GapRisk={m['gap_risk']:.1f} "
            f"({m['gaps']} gaps >2% in {m['lookback']} sessions). "
            f"Accel={m['accel']:.1f}. Risk={risk_score:.1f}."
        )

    # Mixed Risk
    return (
        f"Risk={risk_score:.1f}, Exposure={exposure_score:.1f}. "
        f"Overext={m['overext']:.1f}, EventRisk={m['event_risk']:.1f}, "
        f"VolExp={m['vol_exp']:.1f}, GapRisk={m['gap_risk']:.1f}, "
        f"ConcBoost={m['conc_boost']:.1f}. "
        f"No single dominant driver."
    )


# ---------------------------------------------------------------------------
# Invalidation conditions
# ---------------------------------------------------------------------------

def _invalidation_conditions(
    risk_type: str,
    trim_score: float,
    risk_score: float,
    m: dict,
) -> list:
    if risk_type == "Overextension Risk":
        return [
            f"Price retraces to MA20={m['ma20']:.2f} (currently {m['d20_pct']:+.1f}% above)",
            f"RSI falls below 50 (currently {m['rsi']:.1f})",
            f"Strength deteriorates below 60 — trend signal degrades",
        ]

    if risk_type == "Event Risk":
        return [
            f"Earnings pass in {m['days_str']} days without adverse reaction",
            f"Risk score drops below 40 post-event (currently {risk_score:.1f})",
        ]

    if risk_type == "Concentration Risk":
        return [
            f"Position weight reduced below 10% (currently {m['weight']:.1f}%)",
            f"ConcentrationBoost clears — weight falls to ≤5% "
            f"(currently ConcBoost={m['conc_boost']:.1f})",
            f"Cluster {m['cluster']} weight reduced below 20% "
            f"(currently {m['cluster_wt']:.1f}%)",
        ]

    if risk_type == "Correlation Cluster Risk":
        return [
            f"Cluster {m['cluster']} weight reduced below 20% "
            f"(currently {m['cluster_wt']:.1f}%)",
            f"Cluster members diverge directionally — correlation breaks",
        ]

    if risk_type == "Weak Trend Risk":
        return [
            f"Price reclaims MA20={m['ma20']:.2f} "
            f"(currently {m['d20_pct']:+.1f}% vs MA20)",
            f"TrendPos recovers above 50 (currently {m['trend_pos']:.1f})",
            f"MA50 slope turns positive (currently {m['slope_50']:.3f}%)",
        ]

    if risk_type == "Volatility Risk":
        return [
            f"ATR14/ATR50 ratio normalizes below 1.0 (currently {m['vol_ratio']:.2f})",
            f"Gap count drops to ≤2 in 20 sessions (currently {m['gaps']})",
        ]

    # Mixed Risk
    return [
        f"Trim score drops below 50 (currently {trim_score:.1f})",
        f"Risk score drops below 35 (currently {risk_score:.1f})",
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_trim_explanation(
    trim_score:     float,
    strength_score: float,
    risk_score:     float,
    exposure_score: float,
    risk_comps:     dict,   # raw dicts from compute_* functions (before serialization)
    exp_comps:      dict,
    str_comps:      dict,
    dq_level:       str,
    all_fallbacks:  list,   # combined fallback component names across all score groups
) -> Optional[dict]:
    """
    Returns trim_explanation dict, or None if trim_score < EXPLANATION_THRESHOLD.

    All fields are deterministic and metric-specific.
    """
    if trim_score < EXPLANATION_THRESHOLD:
        return None

    m          = _extract_metrics(risk_comps, exp_comps, str_comps)
    driver     = _primary_driver(risk_score, exposure_score)
    risk_t     = _classify_risk_type(driver, risk_comps, exp_comps, str_comps)
    label      = _action_label(trim_score, risk_score, exposure_score,
                               strength_score, risk_t, risk_comps)
    conf       = _confidence(dq_level, all_fallbacks, driver, risk_t, trim_score)
    narr       = _narrative(risk_t, strength_score, risk_score, exposure_score, m)
    inv_conds  = _invalidation_conditions(risk_t, trim_score, risk_score, m)

    return {
        "action_label":            label,
        "primary_driver":          driver,
        "risk_type":               risk_t,
        "confidence":              conf,
        "narrative":               narr,
        "invalidation_conditions": inv_conds,
    }
