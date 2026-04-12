import type { Position } from '../../types'
import { ScoreBar } from './ScoreBar'
import { scoreColor, trimColor, addColor, actionBadgeClass, opportunityBadgeClass } from '../../utils/scores'

interface Props {
  position: Position
}

export function PositionScores({ position }: Props) {
  const { strength, risk, exposure, trim, upside, recovery, setup_integrity, add,
          trim_explanation, add_explanation, data_quality } = position

  const dqClass = `dq-${data_quality.level}`

  return (
    <>
      {/* DQ tag */}
      {data_quality.level !== 'none' && (
        <div style={{ marginBottom: 14 }}>
          <span className={`dq-tag ${dqClass}`}>
            {data_quality.level.toUpperCase()} — {data_quality.scoring_mode}
          </span>
        </div>
      )}

      {/* Primary scores grid */}
      <div className="detail-score-grid">

        <div className="score-section">
          <div className="score-section-title">Strength</div>
          <div className="score-section-total" style={{ color: scoreColor(strength.score) }}>
            {strength.score.toFixed(1)}
          </div>
          {Object.entries(strength.components).map(([k, v]) => (
            <ScoreBar key={k} label={k} score={v.score}
              color={scoreColor(v.score)} fallback={v.fallback} />
          ))}
        </div>

        <div className="score-section">
          <div className="score-section-title">Risk</div>
          <div className="score-section-total" style={{ color: trimColor(risk.score) }}>
            {risk.score.toFixed(1)}
          </div>
          {Object.entries(risk.components).map(([k, v]) => (
            <ScoreBar key={k} label={k} score={v.score}
              color={trimColor(v.score)} fallback={v.fallback} />
          ))}
        </div>

        <div className="score-section">
          <div className="score-section-title">Upside</div>
          <div className="score-section-total" style={{ color: addColor(upside.score) }}>
            {upside.score.toFixed(1)}
          </div>
          {Object.entries(upside.components).map(([k, v]) => (
            <ScoreBar key={k} label={k} score={v.score}
              color={addColor(v.score)} fallback={v.fallback} />
          ))}
        </div>

        <div className="score-section">
          <div className="score-section-title">Recovery</div>
          <div className="score-section-total" style={{ color: addColor(recovery.score) }}>
            {recovery.score.toFixed(1)}
          </div>
          {Object.entries(recovery.components).map(([k, v]) => (
            <ScoreBar key={k} label={k} score={v.score}
              color={addColor(v.score)} fallback={v.fallback} />
          ))}
        </div>

      </div>

      {/* Composite scores row */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-title">Exposure</div>
          <div className="card-value" style={{ color: trimColor(exposure.score) }}>
            {exposure.score.toFixed(1)}
          </div>
          <div className="card-sub">
            Size {exposure.components.size_score?.score.toFixed(0)} &nbsp;·&nbsp;
            Conc {exposure.components.concentration_boost?.score.toFixed(0)} &nbsp;·&nbsp;
            Corr {exposure.components.correlation_risk?.score.toFixed(0)}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Trim Score{trim.guardrail_1_applied ? ' [GR1]' : ''}</div>
          <div className="card-value" style={{ color: trimColor(trim.score) }}>
            {trim.score.toFixed(1)}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Setup Integrity</div>
          <div className="card-value" style={{ color: scoreColor(setup_integrity.score) }}>
            {setup_integrity.score.toFixed(1)}
          </div>
          <div className="card-sub">
            Penalty: {setup_integrity.total_penalty.toFixed(0)}
          </div>
        </div>
        <div className="card">
          <div className="card-title">
            Add Score
            {add.guardrail_1_applied ? ' [GR1]' : ''}
            {add.guardrail_2_applied ? ' [GR2]' : ''}
          </div>
          <div className="card-value" style={{ color: addColor(add.score) }}>
            {add.score.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Trim explanation */}
      {trim_explanation && (
        <div className="explanation-box trim" style={{ marginBottom: 12 }}>
          <div className="explanation-action">
            <span className={`badge ${actionBadgeClass(trim_explanation.action_label)}`}>
              {trim_explanation.action_label}
            </span>
            <span style={{ marginLeft: 10, color: 'var(--text-muted)', fontSize: 12 }}>
              {trim_explanation.primary_driver} · {trim_explanation.risk_type} · {trim_explanation.confidence}
            </span>
          </div>
          <div className="explanation-narrative" style={{ marginTop: 8 }}>
            {trim_explanation.narrative}
          </div>
          <ul className="explanation-inval">
            {trim_explanation.invalidation_conditions.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Add explanation */}
      {add_explanation && (
        <div className="explanation-box add">
          <div className="explanation-action">
            <span className={`badge ${actionBadgeClass(add_explanation.action_label)}`}>
              {add_explanation.action_label}
            </span>
            <span className={`badge ${opportunityBadgeClass(add_explanation.opportunity_type)}`}
              style={{ marginLeft: 8 }}>
              {add_explanation.opportunity_type}
            </span>
            <span style={{ marginLeft: 10, color: 'var(--text-muted)', fontSize: 12 }}>
              {add_explanation.primary_driver} · {add_explanation.confidence}
            </span>
          </div>
          <div className="explanation-narrative" style={{ marginTop: 8 }}>
            {add_explanation.narrative}
          </div>
          <ul className="explanation-inval">
            {add_explanation.invalidation_conditions.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}
