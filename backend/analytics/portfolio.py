import asyncio
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

from models import (
    Holdings, FullPortfolioAnalysis, PortfolioSummary, PositionAnalysis,
    OptionAnalysis, ClusterExposure, WatchlistItem, AllScores
)
from adapters.base import DataAdapter
from analytics.scoring import PortfolioScorer
from analytics.explanation import ExplanationEngine
from analytics.technical import sma, atr, drawdown_from_peak
from config import CLUSTERS

logger = logging.getLogger(__name__)


class PortfolioAnalyzer:
    def __init__(self, adapter: DataAdapter, scorer: PortfolioScorer, explainer: ExplanationEngine):
        self.adapter = adapter
        self.scorer = scorer
        self.explainer = explainer

    async def analyze(self, holdings: Holdings) -> FullPortfolioAnalysis:
        loop = asyncio.get_event_loop()

        # Collect all tickers
        equity_tickers = [e.ticker for e in holdings.equities]
        etf_tickers = [e.ticker for e in holdings.etfs]
        option_underlyings = list({o.underlying for o in holdings.options})
        all_tickers = list(set(equity_tickers + etf_tickers + option_underlyings + ["SPY"]))

        # Fetch all price data concurrently
        async def fetch(ticker: str) -> Tuple[str, Optional[pd.DataFrame]]:
            try:
                df = await loop.run_in_executor(
                    None, lambda t=ticker: self.adapter.get_price_history(t, 252)
                )
                return ticker, df
            except Exception as e:
                logger.warning(f"Failed to fetch {ticker}: {e}")
                return ticker, None

        async def fetch_earnings(ticker: str) -> Tuple[str, Optional[date]]:
            try:
                d = await loop.run_in_executor(
                    None, lambda t=ticker: self.adapter.get_earnings_date(t)
                )
                return ticker, d
            except Exception as e:
                logger.warning(f"Failed to fetch earnings for {ticker}: {e}")
                return ticker, None

        # Run fetches concurrently
        price_results = await asyncio.gather(*[fetch(t) for t in all_tickers])
        earnings_results = await asyncio.gather(*[fetch_earnings(t) for t in equity_tickers])

        price_data: Dict[str, Optional[pd.DataFrame]] = dict(price_results)
        earnings_data: Dict[str, Optional[date]] = dict(earnings_results)

        spy_df = price_data.get("SPY")

        # Compute position values
        def get_latest_price(ticker: str) -> float:
            df = price_data.get(ticker)
            if df is not None and not df.empty:
                return float(df["close"].iloc[-1])
            return 0.0

        # Build value maps
        equity_values = {}
        for e in holdings.equities:
            p = get_latest_price(e.ticker)
            equity_values[e.ticker] = p * e.quantity

        etf_values = {}
        for e in holdings.etfs:
            p = get_latest_price(e.ticker)
            etf_values[e.ticker] = p * e.quantity

        total_equity = sum(equity_values.values())
        total_etf = sum(etf_values.values())
        total_value = total_equity + total_etf
        if total_value == 0:
            total_value = 1.0  # avoid division by zero

        # All weights (for cluster computation)
        all_weights: Dict[str, float] = {}
        for ticker, val in {**equity_values, **etf_values}.items():
            all_weights[ticker] = val / total_value

        # Score equities
        equity_positions: List[PositionAnalysis] = []
        for holding in holdings.equities:
            ticker = holding.ticker
            df = price_data.get(ticker)
            if df is None or df.empty:
                logger.warning(f"No price data for {ticker}, skipping")
                continue

            try:
                pos_val = equity_values[ticker]
                weight = pos_val / total_value
                latest_price = float(df["close"].iloc[-1])
                earnings_dt = earnings_data.get(ticker)
                days_to_earn = 999
                if earnings_dt is not None:
                    days_to_earn = (earnings_dt - date.today()).days
                    if days_to_earn < 0:
                        days_to_earn = 999

                scores = self.scorer.score_equity(
                    ticker=ticker,
                    price_df=df,
                    spy_df=spy_df,
                    position_weight=weight,
                    position_value=pos_val,
                    total_value=total_value,
                    all_weights=all_weights,
                    earnings_date=earnings_dt,
                )

                metrics = self.scorer.get_metrics(df, spy_df, earnings_dt)

                # Get cluster memberships
                clusters = [name for name, members in CLUSTERS.items() if ticker in members]

                # Generate explanations
                trim_exp = None
                add_exp = None
                if scores.trim >= 35:
                    trim_exp = self.explainer.generate_trim_explanation(
                        ticker=ticker,
                        scores=scores,
                        metrics=metrics,
                        position_weight=weight,
                        cluster_memberships=clusters,
                        all_weights=all_weights,
                    )
                if scores.add_score >= 35:
                    add_exp = self.explainer.generate_add_explanation(
                        ticker=ticker,
                        scores=scores,
                        metrics=metrics,
                        cluster_memberships=clusters,
                        all_weights=all_weights,
                    )

                # Compute MAs and indicators
                close = df["close"]
                high = df["high"]
                low = df["low"]
                ma20 = sma(close, 20).iloc[-1]
                ma50 = sma(close, 50).iloc[-1]
                atr_series = atr(high, low, close, 14)
                atr14 = atr_series.iloc[-1]
                dd_60 = drawdown_from_peak(close, 60)

                def pct_ch(s, n):
                    if len(s) < n + 1:
                        return 0.0
                    return float((s.iloc[-1] - s.iloc[-(n + 1)]) / s.iloc[-(n + 1)])

                pos = PositionAnalysis(
                    ticker=ticker,
                    asset_type="equity",
                    quantity=holding.quantity,
                    latest_price=round(latest_price, 2),
                    position_value=round(pos_val, 2),
                    weight_pct=round(weight * 100, 2),
                    scores=scores,
                    trim_explanation=trim_exp,
                    add_explanation=add_exp,
                    clusters=clusters,
                    days_to_earnings=days_to_earn,
                    pct_change_1d=round(pct_ch(close, 1) * 100, 2),
                    pct_change_5d=round(pct_ch(close, 5) * 100, 2),
                    pct_change_30d=round(pct_ch(close, 30) * 100, 2),
                    ma20=round(float(ma20), 2),
                    ma50=round(float(ma50), 2),
                    rsi14=round(metrics["rsi14"], 1),
                    atr14=round(float(atr14), 4),
                    drawdown_60d=round(dd_60, 1),
                )
                equity_positions.append(pos)

            except Exception as e:
                logger.error(f"Error scoring {ticker}: {e}", exc_info=True)

        # Score ETFs
        etf_positions: List[PositionAnalysis] = []
        for holding in holdings.etfs:
            ticker = holding.ticker
            df = price_data.get(ticker)
            if df is None or df.empty:
                continue

            try:
                pos_val = etf_values[ticker]
                weight = pos_val / total_value
                latest_price = float(df["close"].iloc[-1])

                scores = self.scorer.score_etf(
                    ticker=ticker,
                    price_df=df,
                    spy_df=spy_df,
                    position_weight=weight,
                    position_value=pos_val,
                    total_value=total_value,
                    all_weights=all_weights,
                )

                close = df["close"]
                high = df["high"]
                low = df["low"]
                ma20 = sma(close, 20).iloc[-1]
                ma50 = sma(close, 50).iloc[-1]
                atr_series = atr(high, low, close, 14)
                atr14 = atr_series.iloc[-1]
                dd_60 = drawdown_from_peak(close, 60)
                metrics = self.scorer.get_metrics(df, spy_df, None)

                def pct_ch(s, n):
                    if len(s) < n + 1:
                        return 0.0
                    return float((s.iloc[-1] - s.iloc[-(n + 1)]) / s.iloc[-(n + 1)])

                pos = PositionAnalysis(
                    ticker=ticker,
                    asset_type="etf",
                    quantity=holding.quantity,
                    latest_price=round(latest_price, 2),
                    position_value=round(pos_val, 2),
                    weight_pct=round(weight * 100, 2),
                    scores=scores,
                    trim_explanation=None,
                    add_explanation=None,
                    clusters=[],
                    days_to_earnings=999,
                    pct_change_1d=round(pct_ch(close, 1) * 100, 2),
                    pct_change_5d=round(pct_ch(close, 5) * 100, 2),
                    pct_change_30d=round(pct_ch(close, 30) * 100, 2),
                    ma20=round(float(ma20), 2),
                    ma50=round(float(ma50), 2),
                    rsi14=round(metrics["rsi14"], 1),
                    atr14=round(float(atr14), 4),
                    drawdown_60d=round(dd_60, 1),
                )
                etf_positions.append(pos)

            except Exception as e:
                logger.error(f"Error scoring ETF {ticker}: {e}", exc_info=True)

        # Score options
        option_analyses: List[OptionAnalysis] = []
        options_notional = 0.0
        for opt in holdings.options:
            underlying_price = get_latest_price(opt.underlying)
            if underlying_price == 0:
                underlying_price = 100.0

            opt_scores = self.scorer.score_option(opt, underlying_price, spy_df)
            from datetime import datetime as dt_cls
            try:
                expiry_date = dt_cls.strptime(opt.expiry, "%Y-%m-%d").date()
                days_to_expiry = (expiry_date - date.today()).days
            except Exception:
                days_to_expiry = 365

            notional = opt.strike * opt.contracts * 100
            options_notional += notional

            option_analyses.append(OptionAnalysis(
                underlying=opt.underlying,
                type=opt.type,
                strike=opt.strike,
                expiry=opt.expiry,
                contracts=opt.contracts,
                underlying_price=round(underlying_price, 2),
                notional_exposure=round(notional, 2),
                days_to_expiry=opt_scores["days_to_expiry"],
                moneyness=opt_scores["moneyness"],
                moneyness_pct=opt_scores["moneyness_pct"],
                scenario_note=opt_scores["scenario_note"],
            ))

        # Compute cluster exposures
        cluster_exposures: List[ClusterExposure] = []
        for cluster_name, members in CLUSTERS.items():
            cluster_tickers_held = [t for t in members if t in all_weights]
            if not cluster_tickers_held:
                continue
            cluster_weight = sum(all_weights.get(t, 0.0) for t in cluster_tickers_held) * 100
            if cluster_weight < 0.5:
                continue
            if cluster_weight > 25:
                risk_level = "high"
            elif cluster_weight > 15:
                risk_level = "elevated"
            elif cluster_weight > 5:
                risk_level = "moderate"
            else:
                risk_level = "low"

            cluster_exposures.append(ClusterExposure(
                name=cluster_name,
                weight_pct=round(cluster_weight, 2),
                tickers=cluster_tickers_held,
                risk_level=risk_level,
            ))

        cluster_exposures.sort(key=lambda x: x.weight_pct, reverse=True)

        # Compute top-5 concentration
        all_positions = equity_positions + etf_positions
        sorted_by_val = sorted(all_positions, key=lambda p: p.position_value, reverse=True)
        top5_val = sum(p.position_value for p in sorted_by_val[:5])
        top5_concentration = (top5_val / total_value * 100) if total_value > 0 else 0.0

        # Daily change
        def weighted_daily_change() -> float:
            total_w = 0.0
            total_ch = 0.0
            for pos in all_positions:
                w = pos.position_value / total_value
                total_ch += w * pos.pct_change_1d
                total_w += w
            return total_ch if total_w > 0 else 0.0

        daily_change = weighted_daily_change()

        summary = PortfolioSummary(
            total_value=round(total_value, 2),
            equity_value=round(total_equity, 2),
            etf_value=round(total_etf, 2),
            options_notional=round(options_notional, 2),
            position_count=len(equity_positions) + len(etf_positions),
            top_5_concentration=round(top5_concentration, 1),
            cluster_exposures=cluster_exposures,
            daily_change_pct=round(daily_change, 2),
        )

        # Trim candidates (score >= 35, equity only, sorted desc)
        trim_candidates = sorted(
            [p for p in equity_positions if p.scores.trim >= 35],
            key=lambda p: p.scores.trim,
            reverse=True,
        )

        # Add candidates (score >= 35, equity only, sorted desc)
        add_candidates = sorted(
            [p for p in equity_positions if p.scores.add_score >= 35],
            key=lambda p: p.scores.add_score,
            reverse=True,
        )

        # Watchlist
        watchlist: List[WatchlistItem] = []

        # Earnings watchlist (within 30 days)
        for pos in sorted(equity_positions, key=lambda p: p.days_to_earnings):
            if pos.days_to_earnings <= 30:
                urgency = "high" if pos.days_to_earnings <= 7 else ("medium" if pos.days_to_earnings <= 14 else "low")
                watchlist.append(WatchlistItem(
                    ticker=pos.ticker,
                    reason="Earnings approaching",
                    urgency=urgency,
                    detail=f"Reports in {pos.days_to_earnings} days. Catalyst Risk: {pos.scores.catalyst_risk:.0f}/100",
                ))

        # Large moves (>5% in 5d)
        for pos in equity_positions + etf_positions:
            if abs(pos.pct_change_5d) > 5 and not any(w.ticker == pos.ticker for w in watchlist):
                direction = "up" if pos.pct_change_5d > 0 else "down"
                urgency = "high" if abs(pos.pct_change_5d) > 10 else "medium"
                watchlist.append(WatchlistItem(
                    ticker=pos.ticker,
                    reason=f"Large 5-day move ({direction})",
                    urgency=urgency,
                    detail=f"{pos.pct_change_5d:+.1f}% in 5 days. RSI: {pos.rsi14:.0f}",
                ))

        # High catalyst risk
        for pos in sorted(equity_positions, key=lambda p: p.scores.catalyst_risk, reverse=True)[:5]:
            if pos.scores.catalyst_risk > 60 and not any(w.ticker == pos.ticker for w in watchlist):
                watchlist.append(WatchlistItem(
                    ticker=pos.ticker,
                    reason="High Catalyst Risk",
                    urgency="high" if pos.scores.catalyst_risk > 80 else "medium",
                    detail=f"Catalyst Risk Score: {pos.scores.catalyst_risk:.0f}/100. {pos.scores.risk.event_risk.raw_input}",
                ))

        return FullPortfolioAnalysis(
            summary=summary,
            positions=equity_positions,
            etf_positions=etf_positions,
            options=option_analyses,
            trim_candidates=trim_candidates,
            add_candidates=add_candidates,
            watchlist=watchlist,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
