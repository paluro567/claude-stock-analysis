export interface TopPosition {
  ticker: string
  weight: number
  value: number
}

export interface AssetTypeCounts {
  equity: number
  etf: number
  option: number
  [key: string]: number
}

export interface PortfolioSummaryData {
  total_value: number
  position_count: number
  asset_type_counts: AssetTypeCounts
  concentration_hhi: number
  top_positions: TopPosition[]
}

export interface ClusterExposure {
  tickers: string[]
  total_weight: number
}

export interface PortfolioSummaryResponse {
  summary: PortfolioSummaryData
  cluster_exposures: Record<string, ClusterExposure>
  trim_candidate_count: number
  add_candidate_count: number
  review_queue_count: number
}

export interface ScoreComponent {
  score: number
  fallback: boolean
  fallback_reason: string | null
  [key: string]: unknown
}

export interface ScoreBlock {
  score: number
  components: Record<string, ScoreComponent>
  fallback_components: string[]
}

export interface TrimScore {
  score: number
  raw: number
  guardrail_1_applied: boolean
  inputs: Record<string, number>
}

export interface AddScore {
  score: number
  raw: number
  guardrail_1_applied: boolean
  guardrail_2_applied: boolean
  inputs: Record<string, number>
}

export interface SetupIntegrity {
  score: number
  penalties: { broken_trend: number; high_volatility: number; freefall: number }
  total_penalty: number
  fallback: boolean
  fallback_reason: string | null
}

export interface TrimExplanation {
  action_label: string
  primary_driver: string
  risk_type: string
  confidence: string
  narrative: string
  invalidation_conditions: string[]
}

export interface AddExplanation {
  action_label: string
  primary_driver: string
  opportunity_type: string
  confidence: string
  narrative: string
  invalidation_conditions: string[]
}

export interface DataQuality {
  level: string
  reason_code: string | null
  scoring_mode: string
}

export interface Position {
  ticker: string
  as_of: string
  data_quality: DataQuality
  data_quality_flag: string | null
  strength: ScoreBlock
  risk: ScoreBlock
  exposure: ScoreBlock
  trim: TrimScore
  trim_explanation: TrimExplanation | null
  upside: ScoreBlock
  recovery: ScoreBlock
  setup_integrity: SetupIntegrity
  add: AddScore
  add_explanation: AddExplanation | null
}

export interface TrimCandidateEntry {
  ticker: string
  trim_score: number
  action: string
  primary_driver: string
  risk_type: string
  position: Position
}

export interface TrimCandidatesResponse {
  threshold: number
  count: number
  candidates: TrimCandidateEntry[]
}

export interface AddCandidateEntry {
  ticker: string
  add_score: number
  action: string
  opportunity_type: string
  primary_driver: string
  position: Position
}

export interface AddCandidatesResponse {
  threshold: number
  count: number
  candidates: AddCandidateEntry[]
}

export interface ReviewQueueEntry {
  ticker: string
  flags: string[]
  trim_score: number
  add_score: number
  strength_score: number
  risk_score: number
  exposure_score: number
  position: Position
}

export interface ReviewQueueResponse {
  count: number
  queue: ReviewQueueEntry[]
}
