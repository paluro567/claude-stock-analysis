import logging
from datetime import date
from typing import Optional, Dict, List
import numpy as np
import pandas as pd

from models import (
    AllScores, StrengthScore, RiskScore, ExposureScore, ComponentScore
)
from analytics.technical import (
    sma, atr, rsi as compute_rsi, drawdown_from_peak,
    ma_slope, gap_count, compute_rsi_series
)
from config import CLUSTERS

logger = logging.getLogger(__name__)


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


class PortfolioScorer:

    def score_equity(
        self,
        ticker: str,
        price_df: pd.DataFrame,
        spy_df: pd.DataFrame,
        position_weight: float,
        position_value: float,
        total_value: float,
        all_weights: Dict[str, float],
        earnings_date: Optional[date],
    ) -> AllScores:
        strength = self._strength(price_df, spy_df)
        risk = self._risk(price_df, earnings_date)
        exposure = self._exposure(position_weight, total_value, position_value, all_weights, ticker)
        trim = self._trim(strength.total, risk.total, exposure.total)
        overext = self._overextension(price_df)
        underval = self._undervaluation(price_df, spy_df)
        recovery = self._recovery_confidence(price_df)
        add_sc = self._add_score(underval, recovery, strength.total)
        catalyst = self._catalyst_risk(risk)

        return AllScores(
            strength=strength,
            risk=risk,
            exposure=exposure,
            trim=trim,
            overextension=overext,
            undervaluation=underval,
            recovery_confidence=recovery,
            add_score=add_sc,
            catalyst_risk=catalyst,
        )

    def score_etf(
        self,
        ticker: str,
        price_df: pd.DataFrame,
        spy_df: pd.DataFrame,
        position_weight: float,
        position_value: float,
        total_value: float,
        all_weights: Dict[str, float],
    ) -> AllScores:
        strength = self._strength(price_df, spy_df)
        risk = self._risk(price_df, None)
        exposure = self._exposure(position_weight, total_value, position_value, all_weights, ticker)
        trim = self._trim(strength.total, risk.total, exposure.total)
        overext = self._overextension(price_df)
        # ETFs don't get add scores
        return AllScores(
            strength=strength,
            risk=risk,
            exposure=exposure,
            trim=trim,
            overextension=overext,
            undervaluation=0.0,
            recovery_confidence=0.0,
            add_score=0.0,
            catalyst_risk=self._catalyst_risk(risk),
        )

    def score_option(self, option, underlying_price: float, spy_df: pd.DataFrame) -> dict:
        """Simple option analysis — returns dict with context."""
        from datetime import datetime
        try:
            expiry = datetime.strptime(option.expiry, "%Y-%m-%d").date()
            days_to_expiry = (expiry - date.today()).days
        except Exception:
            days_to_expiry = 365

        moneyness_pct = (underlying_price - option.strike) / option.strike * 100
        if option.type == "CALL":
            if moneyness_pct > 5:
                moneyness = "ITM"
            elif moneyness_pct > -5:
                moneyness = "ATM"
            else:
                moneyness = "OTM"
        else:
            if moneyness_pct < -5:
                moneyness = "ITM"
            elif moneyness_pct < 5:
                moneyness = "ATM"
            else:
                moneyness = "OTM"

        notional = option.strike * option.contracts * 100

        if days_to_expiry < 30:
            scenario = "Near expiry — high theta decay, evaluate roll or close"
        elif moneyness == "OTM" and days_to_expiry < 90:
            scenario = f"OTM with {days_to_expiry}d to expiry — needs {abs(moneyness_pct):.1f}% move to break even"
        elif moneyness == "ITM":
            scenario = f"ITM by {abs(moneyness_pct):.1f}% — consider harvesting intrinsic value or rolling"
        else:
            scenario = f"ATM, {days_to_expiry}d to expiry — monitoring for directional move"

        return {
            "days_to_expiry": days_to_expiry,
            "moneyness": moneyness,
            "moneyness_pct": round(moneyness_pct, 2),
            "notional_exposure": notional,
            "scenario_note": scenario,
        }

    # -------------------------
    # Component Scorers
    # -------------------------

    def _strength(self, price_df: pd.DataFrame, spy_df: pd.DataFrame) -> StrengthScore:
        close = price_df["close"]
        ma20 = sma(close, 20)
        ma50 = sma(close, 50)

        # --- RelativePerf ---
        stock_30d = self._pct_change(close, 30)
        spy_30d = self._pct_change(spy_df["close"], 30) if spy_df is not None and len(spy_df) > 30 else 0.0
        excess = stock_30d - spy_30d
        rel_perf_score = clamp((excess + 0.30) / 0.60 * 100)
        rel_perf_label = f"Stock +{stock_30d*100:.1f}% vs SPY +{spy_30d*100:.1f}% (30d) | excess {excess*100:+.1f}%"

        # --- TrendPositioning ---
        price_now = close.iloc[-1]
        ma20_now = ma20.iloc[-1]
        ma50_now = ma50.iloc[-1]

        pct_vs_20ma = (price_now - ma20_now) / ma20_now * 100 if ma20_now > 0 else 0.0
        pct_vs_50ma = (price_now - ma50_now) / ma50_now * 100 if ma50_now > 0 else 0.0
        score_20 = clamp(50 + pct_vs_20ma * 2.5)
        score_50 = clamp(50 + pct_vs_50ma * 1.5)
        trend_pos_score = 0.6 * score_20 + 0.4 * score_50
        trend_pos_label = f"Price {pct_vs_20ma:+.1f}% vs 20MA, {pct_vs_50ma:+.1f}% vs 50MA"

        # --- TrendStructure ---
        slope_pct = ma_slope(close, ma_period=50, lookback=20)
        trend_struct_score = clamp(50 + slope_pct * 8)
        trend_struct_label = f"50-day MA slope {slope_pct:+.2f}% over last 20 sessions"

        # --- VolumeConfirm ---
        vol_conf_score, vol_conf_label = self._volume_confirm(price_df)

        # --- Stability ---
        dd = drawdown_from_peak(close, 60)
        stability_score = clamp(100 - dd * 2.5)
        stability_label = f"Drawdown {dd:.1f}% from 60-day high"

        total = (
            0.30 * rel_perf_score
            + 0.25 * trend_pos_score
            + 0.20 * trend_struct_score
            + 0.15 * vol_conf_score
            + 0.10 * stability_score
        )

        return StrengthScore(
            total=round(clamp(total), 1),
            relative_perf=ComponentScore(value=round(rel_perf_score, 1), label="Relative Performance (30d)", raw_input=rel_perf_label),
            trend_positioning=ComponentScore(value=round(trend_pos_score, 1), label="Trend Positioning", raw_input=trend_pos_label),
            trend_structure=ComponentScore(value=round(trend_struct_score, 1), label="Trend Structure (50MA slope)", raw_input=trend_struct_label),
            volume_confirm=ComponentScore(value=round(vol_conf_score, 1), label="Volume Confirmation", raw_input=vol_conf_label),
            stability=ComponentScore(value=round(stability_score, 1), label="Stability (60d drawdown)", raw_input=stability_label),
        )

    def _volume_confirm(self, price_df: pd.DataFrame):
        """Volume confirm: ratio of avg vol on up days vs down days (40d)."""
        df = price_df.tail(40)
        if len(df) < 5:
            return 50.0, "Insufficient data"

        close = df["close"]
        vol = df["volume"]
        delta = close.diff()

        up_mask = delta > 0
        dn_mask = delta < 0

        avg_up = vol[up_mask].mean() if up_mask.sum() > 0 else 0.0
        avg_dn = vol[dn_mask].mean() if dn_mask.sum() > 0 else 0.0

        if avg_dn == 0:
            ratio = 2.0
        else:
            ratio = avg_up / avg_dn

        score = clamp((ratio - 0.5) / 1.0 * 100)
        label = f"Up-day vol {avg_up/1e6:.1f}M vs Down-day vol {avg_dn/1e6:.1f}M | ratio {ratio:.2f}"
        return score, label

    def _risk(self, price_df: pd.DataFrame, earnings_date: Optional[date]) -> RiskScore:
        close = price_df["close"]
        high = price_df["high"]
        low = price_df["low"]
        open_ = price_df["open"]

        ma20 = sma(close, 20)
        price_now = close.iloc[-1]
        ma20_now = ma20.iloc[-1]

        # --- Overextension ---
        pct_above_20ma = (price_now - ma20_now) / ma20_now * 100 if ma20_now > 0 else 0.0
        overext_score = clamp(pct_above_20ma * 6)
        overext_label = f"Price {pct_above_20ma:+.1f}% vs 20-day MA"

        # --- RSI Stretch ---
        rsi_val = compute_rsi(close, 14)
        if rsi_val <= 50:
            rsi_score = 0.0
        else:
            rsi_score = clamp((rsi_val - 50) * 4)
        rsi_label = f"RSI 14 = {rsi_val:.1f}"

        # --- Event Risk ---
        if earnings_date is not None:
            days_to_earn = (earnings_date - date.today()).days
            if days_to_earn <= 0:
                days_to_earn = 999  # already passed
        else:
            days_to_earn = 999

        if days_to_earn <= 7:
            event_score = 100.0
        elif days_to_earn <= 14:
            event_score = 80.0
        elif days_to_earn <= 21:
            event_score = 60.0
        elif days_to_earn <= 45:
            event_score = 30.0
        elif days_to_earn <= 90:
            event_score = 15.0
        else:
            event_score = 5.0
        event_label = f"Days to earnings: {days_to_earn if days_to_earn < 999 else 'N/A'}"

        # --- VolExpansion ---
        atr_series = atr(high, low, close, 14)
        atr_50_series = atr(high, low, close, 50)
        atr14_now = atr_series.iloc[-1]
        atr50_now = atr_50_series.iloc[-1]
        vol_ratio = atr14_now / atr50_now if atr50_now > 0 else 1.0
        vol_exp_score = clamp((vol_ratio - 0.5) * 80)
        vol_exp_label = f"ATR14/ATR50 ratio {vol_ratio:.2f} (ATR14={atr14_now:.2f})"

        # --- Acceleration ---
        ret_5d = self._pct_change(close, 5)
        ret_20d = self._pct_change(close, 20)
        daily_pace = abs(ret_20d / 20) + 0.0001
        daily_5d = ret_5d / 5
        if daily_5d != 0 and ret_20d != 0:
            accel_ratio = daily_5d / daily_pace
        else:
            accel_ratio = 0.0
        if accel_ratio > 1:
            accel_score = clamp((accel_ratio - 1) * 60)
        else:
            accel_score = 0.0
        accel_label = f"5d return {ret_5d*100:+.1f}% vs 20d daily pace {daily_pace*100:.2f}%"

        # --- Gap Risk ---
        gaps = gap_count(open_, close, 20, 0.02)
        gap_score = clamp(gaps * 18)
        gap_label = f"{gaps} gaps >2% in last 20 sessions"

        total = (
            0.25 * overext_score
            + 0.20 * rsi_score
            + 0.20 * event_score
            + 0.15 * vol_exp_score
            + 0.10 * accel_score
            + 0.10 * gap_score
        )

        return RiskScore(
            total=round(clamp(total), 1),
            overextension=ComponentScore(value=round(overext_score, 1), label="Overextension vs 20MA", raw_input=overext_label),
            rsi_stretch=ComponentScore(value=round(rsi_score, 1), label="RSI Stretch", raw_input=rsi_label),
            event_risk=ComponentScore(value=round(event_score, 1), label="Event Risk (Earnings)", raw_input=event_label),
            vol_expansion=ComponentScore(value=round(vol_exp_score, 1), label="Volatility Expansion", raw_input=vol_exp_label),
            acceleration=ComponentScore(value=round(accel_score, 1), label="Price Acceleration", raw_input=accel_label),
            gap_risk=ComponentScore(value=round(gap_score, 1), label="Gap Risk", raw_input=gap_label),
        )

    def _exposure(
        self,
        weight: float,
        total_value: float,
        pos_value: float,
        all_weights: Dict[str, float],
        ticker: str,
    ) -> ExposureScore:
        # --- PositionSize ---
        pos_size_score = clamp(weight * 700)
        pos_size_label = f"Position weight {weight*100:.1f}% of portfolio"

        # --- ConcentrationBoost ---
        if weight > 0.15:
            conc_boost = 30.0
        elif weight > 0.10:
            conc_boost = 20.0
        elif weight > 0.05:
            conc_boost = 10.0
        else:
            conc_boost = 0.0
        conc_label = f"Weight {weight*100:.1f}% → concentration boost {conc_boost:.0f}"

        # --- ClusterRisk ---
        cluster_boost = 0.0
        cluster_note = "No significant cluster overlap"
        for cluster_name, members in CLUSTERS.items():
            if ticker in members:
                cluster_weight = sum(all_weights.get(m, 0.0) for m in members)
                if cluster_weight > 0.30:
                    cluster_boost = max(cluster_boost, 10.0)
                    cluster_note = f"{cluster_name} cluster: {cluster_weight*100:.1f}% of portfolio"
                elif cluster_weight > 0.20:
                    cluster_boost = max(cluster_boost, 5.0)
                    cluster_note = f"{cluster_name} cluster: {cluster_weight*100:.1f}% of portfolio"

        total = clamp(pos_size_score + conc_boost + cluster_boost)

        return ExposureScore(
            total=round(total, 1),
            position_size=ComponentScore(value=round(pos_size_score, 1), label="Position Size Score", raw_input=pos_size_label),
            concentration_boost=ComponentScore(value=round(conc_boost, 1), label="Concentration Boost", raw_input=conc_label),
            cluster_risk=ComponentScore(value=round(cluster_boost, 1), label="Cluster Risk Boost", raw_input=cluster_note),
        )

    def _trim(self, strength: float, risk: float, exposure: float) -> float:
        raw = (risk * 0.5) + (exposure * 0.4) - (strength * 0.3)
        trim = clamp(raw)

        # Guardrail: if Strength > 80 and Risk < 60, cap Trim at 55 unless Exposure > 85
        if strength > 80 and risk < 60 and exposure <= 85:
            trim = min(trim, 55.0)

        return round(trim, 1)

    def _overextension(self, price_df: pd.DataFrame) -> float:
        close = price_df["close"]
        high = price_df["high"]
        low = price_df["low"]

        ma20 = sma(close, 20)
        price_now = close.iloc[-1]
        ma20_now = ma20.iloc[-1]

        pct_above_20ma = (price_now - ma20_now) / ma20_now * 100 if ma20_now > 0 else 0.0
        overext_raw = clamp(pct_above_20ma * 6)

        rsi_val = compute_rsi(close, 14)
        rsi_contrib = clamp((rsi_val - 50) * 4) if rsi_val > 50 else 0.0

        ret_5d = self._pct_change(close, 5)
        ret_20d = self._pct_change(close, 20)
        daily_pace = abs(ret_20d / 20) + 0.0001
        accel_ratio = (ret_5d / 5) / daily_pace if ret_5d != 0 else 0.0
        accel_contrib = clamp((accel_ratio - 1) * 60) if accel_ratio > 1 else 0.0

        atr_series = atr(high, low, close, 14)
        atr_50_series = atr(high, low, close, 50)
        atr14_now = atr_series.iloc[-1]
        atr50_now = atr_50_series.iloc[-1]
        vol_ratio = atr14_now / atr50_now if atr50_now > 0 else 1.0
        vol_contrib = clamp((vol_ratio - 0.5) * 80)

        blend = 0.35 * overext_raw + 0.30 * rsi_contrib + 0.20 * accel_contrib + 0.15 * vol_contrib
        return round(clamp(blend), 1)

    def _undervaluation(self, price_df: pd.DataFrame, spy_df: pd.DataFrame) -> float:
        close = price_df["close"]

        dd = drawdown_from_peak(close, 60)
        drawdown_score = clamp(dd * 2.5)

        stock_30d = self._pct_change(close, 30)
        spy_30d = self._pct_change(spy_df["close"], 30) if spy_df is not None and len(spy_df) > 30 else 0.0
        rel_underperform = spy_30d - stock_30d  # positive if stock underperformed SPY
        rel_underperform_score = clamp((rel_underperform + 0.05) / 0.55 * 100)

        # Stability signal: if recent 5d return > -2%, stock is stabilizing
        ret_5d = self._pct_change(close, 5)
        stability_signal = 70.0 if ret_5d > -0.02 else 30.0

        score = 0.4 * drawdown_score + 0.4 * rel_underperform_score + 0.2 * stability_signal
        return round(clamp(score), 1)

    def _recovery_confidence(self, price_df: pd.DataFrame) -> float:
        close = price_df["close"]
        high = price_df["high"]
        low = price_df["low"]

        score = 0.0

        # 5d momentum: if 5d_return > 0 and price > price_5d_ago
        ret_5d = self._pct_change(close, 5)
        if ret_5d > 0:
            score += 30.0

        # Price vs 20d MA
        ma20 = sma(close, 20)
        price_now = close.iloc[-1]
        ma20_now = ma20.iloc[-1]
        pct_vs_20 = (price_now - ma20_now) / ma20_now * 100 if ma20_now > 0 else 0.0
        if pct_vs_20 >= 0:
            score += 20.0
        elif pct_vs_20 >= -5:
            score += 10.0

        # RSI direction: RSI between 30-50 and rising
        rsi_series = compute_rsi_series(close, 14)
        rsi_now = rsi_series.iloc[-1]
        rsi_prev = rsi_series.iloc[-5] if len(rsi_series) >= 5 else rsi_now
        if 30 <= rsi_now <= 50 and rsi_now > rsi_prev:
            score += 20.0

        # ATR stability: atr14 < atr14 20 sessions ago
        atr_series = atr(high, low, close, 14)
        atr_now = atr_series.iloc[-1]
        atr_ago = atr_series.iloc[-20] if len(atr_series) >= 20 else atr_now
        if atr_now < atr_ago:
            score += 15.0

        # Drawdown slowing: if recent daily drawdown decelerating
        # Compare 5d drawdown to 10d drawdown
        dd_5 = drawdown_from_peak(close, 5)
        dd_10 = drawdown_from_peak(close, 10)
        if dd_5 < dd_10:
            score += 15.0

        return round(clamp(score), 1)

    def _add_score(self, underval: float, recovery: float, strength: float) -> float:
        strength_improving = clamp(100 - strength + 20)
        raw = underval * 0.4 + recovery * 0.3 + strength_improving * 0.2 - strength * 0.2
        return round(clamp(raw), 1)

    def _catalyst_risk(self, risk: RiskScore) -> float:
        score = (
            0.5 * risk.event_risk.value
            + 0.3 * risk.vol_expansion.value
            + 0.2 * risk.gap_risk.value
        )
        return round(clamp(score), 1)

    def _pct_change(self, series: pd.Series, periods: int) -> float:
        if len(series) < periods + 1:
            return 0.0
        end = series.iloc[-1]
        start = series.iloc[-(periods + 1)]
        if start <= 0:
            return 0.0
        return float((end - start) / start)

    def get_metrics(self, price_df: pd.DataFrame, spy_df: pd.DataFrame, earnings_date: Optional[date]) -> dict:
        """Extract raw metrics for use in explanations."""
        close = price_df["close"]
        high = price_df["high"]
        low = price_df["low"]
        open_ = price_df["open"]

        ma20 = sma(close, 20)
        ma50 = sma(close, 50)
        price_now = close.iloc[-1]
        ma20_now = ma20.iloc[-1]
        ma50_now = ma50.iloc[-1]

        pct_vs_20ma = (price_now - ma20_now) / ma20_now * 100 if ma20_now > 0 else 0.0
        pct_vs_50ma = (price_now - ma50_now) / ma50_now * 100 if ma50_now > 0 else 0.0
        rsi_val = compute_rsi(close, 14)
        atr_series = atr(high, low, close, 14)
        atr14 = atr_series.iloc[-1]
        dd_60 = drawdown_from_peak(close, 60)

        stock_30d = self._pct_change(close, 30)
        spy_30d = self._pct_change(spy_df["close"], 30) if spy_df is not None and len(spy_df) > 30 else 0.0

        ret_5d = self._pct_change(close, 5)
        ret_1d = self._pct_change(close, 1)

        if earnings_date is not None:
            days_to_earn = (earnings_date - date.today()).days
            if days_to_earn < 0:
                days_to_earn = 999
        else:
            days_to_earn = 999

        gaps = gap_count(open_, close, 20, 0.02)

        return {
            "price": price_now,
            "ma20": ma20_now,
            "ma50": ma50_now,
            "pct_vs_20ma": pct_vs_20ma,
            "pct_vs_50ma": pct_vs_50ma,
            "rsi14": rsi_val,
            "atr14": atr14,
            "drawdown_60d": dd_60,
            "stock_30d_ret": stock_30d,
            "spy_30d_ret": spy_30d,
            "ret_5d": ret_5d,
            "ret_1d": ret_1d,
            "days_to_earnings": days_to_earn,
            "gap_count": gaps,
        }
