"""
main.py — CLI entry point: load holdings, run engine, print results + JSON.

Holdings come from holdings.py (single source of truth).
No external dependencies — pure Python stdlib + local modules.
"""

import json

from engine import run_engine
from portfolio import compute_portfolio_summary
from holdings import build_holdings, build_spy


# ---------------------------------------------------------------------------
# Human-readable summary printer (per-position)
# ---------------------------------------------------------------------------

def print_summary(results: list) -> None:
    print("\n" + "=" * 72)
    print("  PORTFOLIO SCORE SUMMARY")
    print("=" * 72)

    for r in results:
        ticker   = r["ticker"]
        dq       = r["data_quality"]
        strength = r["strength"]
        risk     = r["risk"]
        exposure = r["exposure"]
        trim     = r["trim"]
        flag     = r.get("data_quality_flag") or "OK"

        print(f"\n  {ticker}  [{flag}]  |  DQ: {dq['level']}  |  Mode: {dq['scoring_mode']}")
        print(f"    Strength Score : {strength['score']:5.1f} / 100")
        print(f"    Risk Score     : {risk['score']:5.1f} / 100")
        print(f"    Exposure Score : {exposure['score']:5.1f} / 100")
        gr1 = " [GR1]" if trim.get("guardrail_1_applied") else ""
        print(f"    Trim Score     : {trim['score']:5.1f} / 100{gr1}")

        ss = exposure["components"]["size_score"]
        cb = exposure["components"]["concentration_boost"]
        cr = exposure["components"]["correlation_risk"]
        wt = ss.get("weight", 0.0)
        print(f"    Position Wt    : {wt*100:5.1f}%  |  "
              f"SizeScore={ss['score']:.1f}  "
              f"ConcBoost={cb['score']:.1f}  "
              f"CorrRisk={cr['score']:.1f}  "
              f"(cluster: {cr.get('primary_cluster') or 'none'})")

        print(f"\n    {'Strength':<16}  {'Score':>6}    {'Risk':<16}  {'Score':>6}")
        print(f"    {'-'*16}  {'-'*6}    {'-'*16}  {'-'*6}")
        s_items = list(strength["components"].items())
        r_items = list(risk["components"].items())
        for i in range(max(len(s_items), len(r_items))):
            sn = s_items[i][0] if i < len(s_items) else ""
            sv = f"{s_items[i][1]['score']:6.1f}" if i < len(s_items) else ""
            rn = r_items[i][0] if i < len(r_items) else ""
            rv = f"{r_items[i][1]['score']:6.1f}" if i < len(r_items) else ""
            print(f"    {sn:<16}  {sv:>6}    {rn:<16}  {rv:>6}")

        s_fb = strength["fallback_components"]
        r_fb = risk["fallback_components"]
        e_fb = exposure["fallback_components"]
        if s_fb: print(f"    Strength fallbacks : {', '.join(s_fb)}")
        if r_fb: print(f"    Risk fallbacks     : {', '.join(r_fb)}")
        if e_fb: print(f"    Exposure fallbacks : {', '.join(e_fb)}")

        expl = r.get("trim_explanation")
        if expl:
            print(f"\n    -- Trim Explanation --")
            print(f"    Action   : {expl['action_label']}")
            print(f"    Driver   : {expl['primary_driver']}  |  Risk type: {expl['risk_type']}")
            print(f"    Confidence: {expl['confidence']}")
            print(f"    Narrative: {expl['narrative']}")
            print(f"    Invalidation:")
            for cond in expl["invalidation_conditions"]:
                print(f"      • {cond}")

        upside   = r["upside"]
        recovery = r["recovery"]
        sis      = r["setup_integrity"]
        add      = r["add"]

        print(f"\n    --- Upside / Recovery / Add ---")
        gr1 = " [GR1]" if add.get("guardrail_1_applied") else ""
        gr2 = " [GR2]" if add.get("guardrail_2_applied") else ""
        print(f"    Upside Score   : {upside['score']:5.1f} / 100")
        print(f"    Recovery Score : {recovery['score']:5.1f} / 100")
        print(f"    Setup Integrity: {sis['score']:5.1f} / 100  "
              f"(penalties: broken={sis['penalties']['broken_trend']:.0f}  "
              f"vol={sis['penalties']['high_volatility']:.0f}  "
              f"freefall={sis['penalties']['freefall']:.0f})")
        print(f"    Add Score      : {add['score']:5.1f} / 100{gr1}{gr2}")

        uv_items = list(upside["components"].items())
        rc_items = list(recovery["components"].items())
        print(f"\n    {'Upside':<22}  {'Score':>6}    {'Recovery':<22}  {'Score':>6}")
        print(f"    {'-'*22}  {'-'*6}    {'-'*22}  {'-'*6}")
        for i in range(max(len(uv_items), len(rc_items))):
            un = uv_items[i][0] if i < len(uv_items) else ""
            uv = f"{uv_items[i][1]['score']:6.1f}" if i < len(uv_items) else ""
            rn = rc_items[i][0] if i < len(rc_items) else ""
            rv = f"{rc_items[i][1]['score']:6.1f}" if i < len(rc_items) else ""
            print(f"    {un:<22}  {uv:>6}    {rn:<22}  {rv:>6}")

        uv_fb = upside["fallback_components"]
        rc_fb = recovery["fallback_components"]
        if uv_fb: print(f"    Upside fallbacks   : {', '.join(uv_fb)}")
        if rc_fb: print(f"    Recovery fallbacks : {', '.join(rc_fb)}")

        add_expl = r.get("add_explanation")
        if add_expl:
            print(f"\n    -- Add Explanation --")
            print(f"    Action   : {add_expl['action_label']}")
            print(f"    Driver   : {add_expl['primary_driver']}  |  "
                  f"Opportunity: {add_expl['opportunity_type']}")
            print(f"    Confidence: {add_expl['confidence']}")
            print(f"    Narrative: {add_expl['narrative']}")
            print(f"    Invalidation:")
            for cond in add_expl["invalidation_conditions"]:
                print(f"      • {cond}")

    print("\n" + "=" * 72 + "\n")


# ---------------------------------------------------------------------------
# Portfolio-level summary printer
# ---------------------------------------------------------------------------

def print_portfolio(portfolio: dict) -> None:
    summ     = portfolio["summary"]
    clusters = portfolio["cluster_exposures"]
    trims    = portfolio["trim_candidates"]
    adds     = portfolio["add_candidates"]
    queue    = portfolio["review_queue"]

    print("\n" + "=" * 72)
    print("  PORTFOLIO OVERVIEW")
    print("=" * 72)

    print(f"\n  Total Value      : ${summ['total_value']:,.2f}")
    print(f"  Positions        : {summ['position_count']}")
    ac = summ["asset_type_counts"]
    print(f"  Asset Types      : equity={ac.get('equity',0)}  "
          f"etf={ac.get('etf',0)}  option={ac.get('option',0)}")
    print(f"  Concentration HHI: {summ['concentration_hhi']:.0f}  "
          f"(>2500 = high, >1500 = moderate)")

    print(f"\n  Top Positions:")
    for p in summ["top_positions"]:
        print(f"    {p['ticker']:<12}  {p['weight']*100:5.1f}%  ${p['value']:>12,.2f}")

    if clusters:
        print(f"\n  Cluster Exposures:")
        for name, data in clusters.items():
            tickers_str = ", ".join(data["tickers"])
            print(f"    {name:<16}  {data['total_weight']*100:5.1f}%  [{tickers_str}]")

    print(f"\n  Trim Candidates  ({len(trims)} flagged):")
    if trims:
        print(f"    {'Ticker':<12}  {'TrimScore':>9}  {'Action':<28}  Driver")
        print(f"    {'-'*12}  {'-'*9}  {'-'*28}  {'-'*20}")
        for t in trims:
            print(f"    {t['ticker']:<12}  {t['trim_score']:>9.1f}  "
                  f"{t['action']:<28}  {t['primary_driver']}")
    else:
        print("    none")

    print(f"\n  Add Candidates   ({len(adds)} flagged):")
    if adds:
        print(f"    {'Ticker':<12}  {'AddScore':>8}  {'Action':<22}  Opportunity")
        print(f"    {'-'*12}  {'-'*8}  {'-'*22}  {'-'*24}")
        for a in adds:
            print(f"    {a['ticker']:<12}  {a['add_score']:>8.1f}  "
                  f"{a['action']:<22}  {a['opportunity_type']}")
    else:
        print("    none")

    print(f"\n  Review Queue     ({len(queue)} positions):")
    if queue:
        print(f"    {'Ticker':<12}  {'Trim':>6}  {'Add':>6}  {'S':>5}  {'R':>5}  {'E':>5}  Flags")
        print(f"    {'-'*12}  {'-'*6}  {'-'*6}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*36}")
        for q in queue:
            flags_str = ", ".join(q["flags"])
            print(f"    {q['ticker']:<12}  {q['trim_score']:>6.1f}  {q['add_score']:>6.1f}  "
                  f"{q['strength_score']:>5.1f}  {q['risk_score']:>5.1f}  "
                  f"{q['exposure_score']:>5.1f}  {flags_str}")
    else:
        print("    none")

    print("\n" + "=" * 72 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    holdings  = build_holdings()
    spy_ohlcv = build_spy()

    results   = run_engine(holdings, spy_ohlcv)
    portfolio = compute_portfolio_summary(holdings, results)

    print_summary(results)
    print_portfolio(portfolio)

    print("--- FULL JSON OUTPUT ---")
    output = {"positions": results, "portfolio": portfolio}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
