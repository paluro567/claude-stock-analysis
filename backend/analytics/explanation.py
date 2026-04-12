import logging
from typing import Dict, List, Optional

from models import AllScores, TrimExplanation, AddExplanation
from config import CLUSTERS

logger = logging.getLogger(__name__)


class ExplanationEngine:

    def generate_trim_explanation(
        self,
        ticker: str,
        scores: AllScores,
        metrics: dict,
        position_weight: float,
        cluster_memberships: List[str],
        all_weights: Dict[str, float],
    ) -> TrimExplanation:
        strength = scores.strength.total
        risk = scores.risk.total
        exposure = scores.exposure.total
        trim = scores.trim

        # Score breakdown string
        score_breakdown = (
            f"Trim Score {trim:.0f} driven primarily by "
            f"{'Risk' if risk >= exposure else 'Exposure'} "
            f"({'Risk' if risk >= exposure else 'Exposure'} = "
            f"{'%.0f' % risk if risk >= exposure else '%.0f' % exposure}), "
            f"partially offset by Strength ({strength:.0f})"
        )

        # Determine primary risk type and reason
        pct_above_ma = metrics.get("pct_vs_20ma", 0.0)
        rsi_val = metrics.get("rsi14", 50.0)
        days_earn = metrics.get("days_to_earnings", 999)
        dd = metrics.get("drawdown_60d", 0.0)
        weight_pct = position_weight * 100

        # Find dominant risk driver
        overext_contrib = scores.risk.overextension.value * 0.25
        event_contrib = scores.risk.event_risk.value * 0.20
        conc_contrib = exposure * 0.4

        drivers = {
            "overextension": overext_contrib + scores.risk.rsi_stretch.value * 0.20,
            "event": event_contrib,
            "concentration": conc_contrib if exposure > 50 else 0,
        }

        # Check cluster concentration
        dominant_cluster = ""
        dominant_cluster_weight = 0.0
        for cluster_name in cluster_memberships:
            members = CLUSTERS.get(cluster_name, [])
            cw = sum(all_weights.get(m, 0.0) for m in members) * 100
            if cw > dominant_cluster_weight:
                dominant_cluster_weight = cw
                dominant_cluster = cluster_name

        cluster_is_dominant = dominant_cluster_weight > 20 and exposure > 40

        primary_driver = max(drivers, key=lambda k: drivers[k])

        # Generate specific primary reason
        if primary_driver == "overextension" or (pct_above_ma > 10 and risk > exposure):
            risk_type = "Overextension Risk"

            if days_earn <= 21 and days_earn < 999:
                primary_reason = (
                    f"{ticker} is {pct_above_ma:+.1f}% above its 20-day MA "
                    f"entering an earnings window in {days_earn} days, "
                    f"creating elevated reversal risk. RSI at {rsi_val:.0f} indicates "
                    f"{'overbought territory' if rsi_val > 70 else 'stretched conditions'}."
                )
            elif pct_above_ma > 15:
                primary_reason = (
                    f"{ticker} is {pct_above_ma:.1f}% extended above its 20-day MA "
                    f"with RSI at {rsi_val:.0f}. "
                    f"{'Momentum is accelerating, increasing mean-reversion risk.' if scores.risk.acceleration.value > 40 else 'Historically, extensions of this magnitude tend to revert within 10-20 sessions.'}"
                )
            else:
                primary_reason = (
                    f"RSI at {rsi_val:.0f} with price {pct_above_ma:+.1f}% from 20-day MA. "
                    f"Volume expansion ratio is elevated — risk/reward for new exposure is unfavorable."
                )

        elif primary_driver == "event" or (days_earn <= 21 and days_earn < 999 and event_contrib > 15):
            risk_type = "Event Risk"
            primary_reason = (
                f"Earnings in {days_earn} days creates binary event exposure. "
                f"Current price is {pct_above_ma:+.1f}% {'above' if pct_above_ma >= 0 else 'below'} "
                f"the 20-day MA, and RSI at {rsi_val:.0f} leaves limited buffer against a negative surprise."
            )

        elif primary_driver == "concentration" or exposure > 70:
            if cluster_is_dominant:
                risk_type = "Correlation Cluster Risk"
                primary_reason = (
                    f"Position represents {weight_pct:.1f}% of portfolio and sits within the "
                    f"'{dominant_cluster}' cluster ({dominant_cluster_weight:.1f}% total exposure). "
                    f"Concentration — not trend quality — is the dominant risk driver here."
                )
            else:
                risk_type = "Concentration Risk"
                primary_reason = (
                    f"Position represents {weight_pct:.1f}% of portfolio. "
                    f"At this sizing, even a moderate {dd:.0f}% drawdown from peak creates "
                    f"meaningful P&L impact independent of thesis quality."
                )
        else:
            risk_type = "Weak Trend Risk" if strength < 45 else "Volatility Risk"
            primary_reason = (
                f"Strength score {strength:.0f} with {scores.risk.gap_risk.raw_input}. "
                f"Price {pct_above_ma:+.1f}% from 20-day MA and "
                f"ATR expansion suggests increasing intraday volatility."
            )

        # Action label
        if trim >= 70:
            action_label = "High Priority Trim"
        elif trim >= 55:
            action_label = "Partial Trim Candidate"
        elif strength > 75 and risk < 55:
            action_label = "Extended but Trend Intact"
        else:
            action_label = "Monitor Only"

        # Invalidation
        ma20_price = metrics.get("ma20", 0.0)
        if primary_driver == "overextension":
            invalidation = (
                f"Price consolidates back toward 20-day MA (${ma20_price:.2f}); "
                f"RSI resets below 60; Risk Score drops below 50."
            )
        elif primary_driver == "event":
            invalidation = (
                f"Earnings pass without a significant gap; price holds above 20-day MA "
                f"(${ma20_price:.2f}) on post-earnings reaction."
            )
        else:
            invalidation = (
                f"Position reduced to below {max(weight_pct - 2, 1):.1f}% of portfolio; "
                f"or price demonstrates sustained hold above 20-day MA (${ma20_price:.2f})."
            )

        # Catalyst note
        if days_earn < 999 and days_earn <= 45:
            catalyst_note = f"Earnings in {days_earn} days — binary event risk {'elevated' if days_earn <= 14 else 'approaching'}."
        elif scores.risk.gap_risk.value > 50:
            catalyst_note = f"Elevated gap frequency ({metrics.get('gap_count', 0)} gaps >2% in 20 sessions) — catalyst sensitivity high."
        else:
            catalyst_note = "No imminent catalyst within 45 days."

        # Portfolio context
        if exposure > risk and exposure > 60:
            portfolio_context = f"Primary driver is position sizing ({weight_pct:.1f}% of portfolio), not trend weakness."
        elif cluster_is_dominant:
            portfolio_context = f"Primary driver is cluster concentration — '{dominant_cluster}' at {dominant_cluster_weight:.1f}% of portfolio."
        else:
            portfolio_context = "Primary driver is stock-specific overextension and momentum."

        return TrimExplanation(
            score_breakdown=score_breakdown,
            primary_reason=primary_reason,
            risk_type=risk_type,
            action_label=action_label,
            invalidation=invalidation,
            catalyst_note=catalyst_note,
            portfolio_context=portfolio_context,
        )

    def generate_add_explanation(
        self,
        ticker: str,
        scores: AllScores,
        metrics: dict,
        cluster_memberships: List[str],
        all_weights: Dict[str, float],
    ) -> AddExplanation:
        dd = metrics.get("drawdown_60d", 0.0)
        spy_30d = metrics.get("spy_30d_ret", 0.0) * 100
        stock_30d = metrics.get("stock_30d_ret", 0.0) * 100
        rsi_val = metrics.get("rsi14", 50.0)
        ma20 = metrics.get("ma20", 0.0)
        ma50 = metrics.get("ma50", 0.0)
        pct_vs_20ma = metrics.get("pct_vs_20ma", 0.0)
        ret_5d = metrics.get("ret_5d", 0.0) * 100
        price = metrics.get("price", 0.0)

        # Why undervalued
        if dd > 20:
            why = (
                f"Down {dd:.0f}% from 60-day high vs SPY {spy_30d:+.1f}% over the same period, "
                f"suggesting selling pressure beyond market conditions. "
                f"Stock has underperformed SPY by {stock_30d - spy_30d:+.1f}% over 30 days."
            )
        elif stock_30d < spy_30d - 5:
            why = (
                f"Underperformed SPY by {spy_30d - stock_30d:.1f}% over 30 days "
                f"({stock_30d:+.1f}% vs SPY {spy_30d:+.1f}%). "
                f"Off {dd:.0f}% from 60-day high — relative weakness suggests potential mean reversion opportunity."
            )
        else:
            why = (
                f"Down {dd:.0f}% from 60-day high with {stock_30d:+.1f}% 30-day return. "
                f"Undervaluation score reflects combination of drawdown and relative underperformance vs SPY."
            )

        # Recovery support
        supports = []
        if ret_5d > 0:
            supports.append(f"price stabilizing over past 5 days (+{ret_5d:.1f}%)")
        if 30 <= rsi_val <= 50:
            supports.append(f"RSI at {rsi_val:.0f} in recovery zone (30-50 range)")
        elif rsi_val < 35:
            supports.append(f"RSI at {rsi_val:.0f} indicating deeply oversold conditions")
        if pct_vs_20ma > -5:
            supports.append(f"price within 5% of 20-day MA (${ma20:.2f})")
        if scores.risk.vol_expansion.value < 40:
            supports.append("volatility compressing (lower ATR14/ATR50 ratio)")

        if supports:
            recovery_support = f"Recovery signals present: {', '.join(supports)}."
        else:
            recovery_support = (
                f"Limited recovery confirmation so far — RSI at {rsi_val:.0f}, "
                f"price {pct_vs_20ma:+.1f}% from 20-day MA. "
                f"Consider waiting for a close above ${ma20:.2f} as entry confirmation."
            )

        # Invalidation
        recent_low = price * (1 - 0.05)  # approximate recent support
        if ma50 > 0:
            key_support = min(ma50, price * 0.93)
            invalidation = (
                f"Continued breakdown below ${key_support:.2f} (50-day MA: ${ma50:.2f}) "
                f"would signal thesis deterioration. Exit if 5-day closing momentum turns negative again."
            )
        else:
            invalidation = (
                f"Breakdown below ${recent_low:.2f} on volume would signal continued distribution. "
                f"Monitor for 5-day negative streak as exit signal."
            )

        # Cluster caution
        cluster_caution = ""
        for cluster_name in cluster_memberships:
            members = CLUSTERS.get(cluster_name, [])
            cw = sum(all_weights.get(m, 0.0) for m in members) * 100
            if cw > 20:
                cluster_caution = (
                    f"Note: Already in large '{cluster_name}' cluster "
                    f"({cw:.1f}% of portfolio) — adding increases cluster concentration risk."
                )
                break

        return AddExplanation(
            why_undervalued=why,
            recovery_support=recovery_support,
            invalidation=invalidation,
            cluster_caution=cluster_caution,
        )
