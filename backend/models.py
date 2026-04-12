from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class EquityHolding(BaseModel):
    ticker: str
    quantity: float
    notes: str = ""


class ETFHolding(BaseModel):
    ticker: str
    quantity: float
    notes: str = ""


class OptionHolding(BaseModel):
    underlying: str
    type: str  # "CALL" or "PUT"
    strike: float
    expiry: str
    contracts: int
    notes: str = ""


class Holdings(BaseModel):
    equities: List[EquityHolding] = []
    etfs: List[ETFHolding] = []
    options: List[OptionHolding] = []


class ComponentScore(BaseModel):
    value: float
    label: str
    raw_input: str


class StrengthScore(BaseModel):
    total: float
    relative_perf: ComponentScore
    trend_positioning: ComponentScore
    trend_structure: ComponentScore
    volume_confirm: ComponentScore
    stability: ComponentScore


class RiskScore(BaseModel):
    total: float
    overextension: ComponentScore
    rsi_stretch: ComponentScore
    event_risk: ComponentScore
    vol_expansion: ComponentScore
    acceleration: ComponentScore
    gap_risk: ComponentScore


class ExposureScore(BaseModel):
    total: float
    position_size: ComponentScore
    concentration_boost: ComponentScore
    cluster_risk: ComponentScore


class AllScores(BaseModel):
    strength: StrengthScore
    risk: RiskScore
    exposure: ExposureScore
    trim: float
    overextension: float
    undervaluation: float
    recovery_confidence: float
    add_score: float
    catalyst_risk: float


class TrimExplanation(BaseModel):
    score_breakdown: str
    primary_reason: str
    risk_type: str
    action_label: str
    invalidation: str
    catalyst_note: str
    portfolio_context: str


class AddExplanation(BaseModel):
    why_undervalued: str
    recovery_support: str
    invalidation: str
    cluster_caution: str


class PositionAnalysis(BaseModel):
    ticker: str
    asset_type: str  # 'equity' | 'etf'
    quantity: float
    latest_price: float
    position_value: float
    weight_pct: float
    scores: AllScores
    trim_explanation: Optional[TrimExplanation] = None
    add_explanation: Optional[AddExplanation] = None
    clusters: List[str] = []
    days_to_earnings: int
    pct_change_1d: float
    pct_change_5d: float
    pct_change_30d: float
    ma20: float
    ma50: float
    rsi14: float
    atr14: float
    drawdown_60d: float


class OptionAnalysis(BaseModel):
    underlying: str
    type: str
    strike: float
    expiry: str
    contracts: int
    underlying_price: float
    notional_exposure: float
    days_to_expiry: int
    moneyness: str
    moneyness_pct: float
    scenario_note: str


class ClusterExposure(BaseModel):
    name: str
    weight_pct: float
    tickers: List[str]
    risk_level: str  # 'low' | 'moderate' | 'elevated' | 'high'


class PortfolioSummary(BaseModel):
    total_value: float
    equity_value: float
    etf_value: float
    options_notional: float
    position_count: int
    top_5_concentration: float
    cluster_exposures: List[ClusterExposure]
    daily_change_pct: float


class WatchlistItem(BaseModel):
    ticker: str
    reason: str
    urgency: str  # 'high' | 'medium' | 'low'
    detail: str


class FullPortfolioAnalysis(BaseModel):
    summary: PortfolioSummary
    positions: List[PositionAnalysis]
    etf_positions: List[PositionAnalysis]
    options: List[OptionAnalysis]
    trim_candidates: List[PositionAnalysis]
    add_candidates: List[PositionAnalysis]
    watchlist: List[WatchlistItem]
    generated_at: str


class PositionDetailResponse(BaseModel):
    position: PositionAnalysis
    price_history: List[dict]
    spy_history: List[dict]
