"""
portfolio.py — Portfolio-level aggregation, ranking, and review queue.

Input:
    holdings : list of holding dicts (same schema as engine input)
    results  : list of scored ticker dicts (output of run_engine)

Output schema:
    {
        "summary": {
            "total_value":       float,
            "position_count":    int,
            "asset_type_counts": {"equity": int, "etf": int, "option": int},
            "concentration_hhi": float,   # Herfindahl index ×10 000
            "top_positions":     [{"ticker", "weight", "value"}, ...],
        },
        "cluster_exposures": {
            cluster_name: {"tickers": [...], "total_weight": float}
        },
        "trim_candidates": [
            {"ticker", "trim_score", "action", "primary_driver", "risk_type"}
        ],
        "add_candidates": [
            {"ticker", "add_score", "action", "opportunity_type", "primary_driver"}
        ],
        "review_queue": [
            {"ticker", "flags", "trim_score", "add_score",
             "strength_score", "risk_score", "exposure_score"}
        ],
    }

All lists are sorted descending by their primary score.
Pure Python, no external dependencies.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRIM_DISPLAY_THRESHOLD    = 25.0    # mirrors explanation.EXPLANATION_THRESHOLD

# Add candidates — only "High Conviction Add" scores qualify for the display
# list.  Watchlist names (60-64) are excluded; they appear in the detail view
# but not in the aggregated add-candidates endpoint.
ADD_DISPLAY_THRESHOLD     = 65.0

# Review queue — same bar as display list so only genuinely actionable adds
# surface in the queue.
ADD_REVIEW_THRESHOLD      = 65.0

# Review queue — positions whose SOLE qualifying flag is add_candidate must
# clear this higher bar to appear (avoids queue bloat from borderline adds
# that have no trim urgency, catalyst risk, or concentration concern).
ADD_SOLO_THRESHOLD        = 70.0

# Review queue — flag concentration_risk only when a position's own exposure
# score is clearly elevated (≥70 keeps it to the true outliers: NOW, CRM,
# ADBE; excludes AMZN/NVDA which are large but not outlier-concentrated).
EXPOSURE_REVIEW_THRESHOLD = 70.0

HIGH_CATALYST_THRESHOLD   = 60.0    # event_risk score
TOP_POSITIONS_N           = 5
HHI_SCALE                 = 10_000  # multiply Σ(w²) to get standard HHI


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _position_weights(holdings: list) -> tuple:
    """
    Compute position value and weight for each holding.
    Returns (positions list, total_value).
    """
    positions = []
    for h in holdings:
        ticker = h["ticker"]
        qty    = h.get("quantity", 0.0)
        close  = h["ohlcv"]["close"]
        value  = close[0] * qty if close else 0.0
        atype  = h.get("asset_type", "equity").lower()
        positions.append({"ticker": ticker, "value": value, "asset_type": atype})

    total = sum(p["value"] for p in positions)
    for p in positions:
        p["weight"] = p["value"] / total if total > 0 else 0.0

    return positions, total


def _cluster_exposures(results: list) -> dict:
    """
    Aggregate cluster exposures across all scored tickers.

    cluster_weight is computed in the engine as Σ(portfolio weights of cluster
    members), so it is the same value for every portfolio ticker that belongs
    to that cluster.  We store it once and collect which tickers appear.
    """
    exposures = {}
    for r in results:
        ticker = r["ticker"]
        cr     = (r.get("exposure", {})
                    .get("components", {})
                    .get("correlation_risk", {}))
        for cluster_name, detail in cr.get("cluster_detail", {}).items():
            if cluster_name not in exposures:
                exposures[cluster_name] = {
                    "tickers":      [],
                    "total_weight": detail.get("cluster_weight", 0.0),
                }
            if ticker not in exposures[cluster_name]["tickers"]:
                exposures[cluster_name]["tickers"].append(ticker)

    return dict(
        sorted(exposures.items(), key=lambda kv: kv[1]["total_weight"], reverse=True)
    )


def _trim_candidates(results: list) -> list:
    """
    Positions with trim_score >= TRIM_DISPLAY_THRESHOLD, sorted descending.
    """
    candidates = []
    for r in results:
        score = r.get("trim", {}).get("score", 0.0)
        if score >= TRIM_DISPLAY_THRESHOLD:
            expl = r.get("trim_explanation") or {}
            candidates.append({
                "ticker":         r["ticker"],
                "trim_score":     score,
                "action":         expl.get("action_label", ""),
                "primary_driver": expl.get("primary_driver", ""),
                "risk_type":      expl.get("risk_type", ""),
            })
    candidates.sort(key=lambda x: x["trim_score"], reverse=True)
    return candidates


def _add_candidates(results: list) -> list:
    """
    Positions with add_score >= ADD_DISPLAY_THRESHOLD, sorted descending.
    Threshold is set to only surface High Conviction Add and strong Watchlist
    names — Monitor-level scores are excluded.
    """
    candidates = []
    for r in results:
        score = r.get("add", {}).get("score", 0.0)
        if score >= ADD_DISPLAY_THRESHOLD:
            expl = r.get("add_explanation") or {}
            candidates.append({
                "ticker":           r["ticker"],
                "add_score":        score,
                "action":           expl.get("action_label", ""),
                "opportunity_type": expl.get("opportunity_type", ""),
                "primary_driver":   expl.get("primary_driver", ""),
            })
    candidates.sort(key=lambda x: x["add_score"], reverse=True)
    return candidates


def _review_queue(results: list) -> list:
    """
    Positions flagged for manual review under any of:
      - trim_score   >= TRIM_DISPLAY_THRESHOLD   — active trim candidate
      - add_score    >= ADD_REVIEW_THRESHOLD      — high-conviction add opportunity
      - event_risk   >= HIGH_CATALYST_THRESHOLD   — upcoming catalyst / earnings
      - exposure_score >= EXPOSURE_REVIEW_THRESHOLD — position-level concentration

    Sorted by trim_score descending (trim urgency first), then add_score descending.
    """
    queue = []
    for r in results:
        trim_score     = r.get("trim",     {}).get("score", 0.0)
        add_score      = r.get("add",      {}).get("score", 0.0)
        exposure_score = r.get("exposure", {}).get("score", 0.0)

        risk_comps = r.get("risk", {}).get("components", {})
        event_risk = risk_comps.get("event_risk", {}).get("score", 0.0)

        flags = []
        if trim_score >= TRIM_DISPLAY_THRESHOLD:
            flags.append("trim_candidate")
        if add_score >= ADD_REVIEW_THRESHOLD:
            flags.append("add_candidate")
        if event_risk >= HIGH_CATALYST_THRESHOLD:
            flags.append("high_catalyst_risk")
        if exposure_score >= EXPOSURE_REVIEW_THRESHOLD:
            flags.append("concentration_risk")

        # Solo-add gate: if the ONLY flag is add_candidate and the score does
        # not clear the higher ADD_SOLO_THRESHOLD bar, drop the position from
        # the queue.  It still appears on the add-candidates list but does not
        # need manual review urgency.
        if flags == ["add_candidate"] and add_score < ADD_SOLO_THRESHOLD:
            flags = []

        if flags:
            queue.append({
                "ticker":         r["ticker"],
                "flags":          flags,
                "trim_score":     trim_score,
                "add_score":      add_score,
                "strength_score": r.get("strength", {}).get("score", 0.0),
                "risk_score":     r.get("risk",     {}).get("score", 0.0),
                "exposure_score": exposure_score,
            })

    queue.sort(key=lambda x: (x["trim_score"], x["add_score"]), reverse=True)
    return queue


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_portfolio_summary(holdings: list, results: list) -> dict:
    """
    Aggregate all results into a portfolio-level summary dict.

    Parameters
    ----------
    holdings : list of holding dicts (ticker, quantity, ohlcv, ...)
    results  : list of scored ticker dicts from run_engine()

    Returns
    -------
    dict with keys: summary, cluster_exposures, trim_candidates,
                    add_candidates, review_queue
    """
    positions, total_value = _position_weights(holdings)

    asset_counts = {"equity": 0, "etf": 0, "option": 0}
    for p in positions:
        t = p["asset_type"]
        if t in asset_counts:
            asset_counts[t] += 1
        else:
            asset_counts[t] = 1

    hhi   = sum(p["weight"] ** 2 for p in positions) * HHI_SCALE
    top_n = sorted(positions, key=lambda x: x["weight"], reverse=True)[:TOP_POSITIONS_N]

    return {
        "summary": {
            "total_value":       round(total_value, 2),
            "position_count":    len(positions),
            "asset_type_counts": asset_counts,
            "concentration_hhi": round(hhi, 2),
            "top_positions": [
                {
                    "ticker": p["ticker"],
                    "weight": round(p["weight"], 6),
                    "value":  round(p["value"],  2),
                }
                for p in top_n
            ],
        },
        "cluster_exposures": {
            name: {
                "tickers":      data["tickers"],
                "total_weight": round(data["total_weight"], 6),
            }
            for name, data in _cluster_exposures(results).items()
        },
        "trim_candidates": _trim_candidates(results),
        "add_candidates":  _add_candidates(results),
        "review_queue":    _review_queue(results),
    }
