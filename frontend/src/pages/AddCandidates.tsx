import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Header } from '../components/layout/Header'
import { Spinner, ErrorMessage } from '../components/common/Spinner'
import { ScoreBar } from '../components/common/ScoreBar'
import { addColor, scoreColor, actionBadgeClass, opportunityBadgeClass } from '../utils/scores'

export function AddCandidates() {
  const { data, loading, error } = useApi(api.getAddCandidates)

  return (
    <>
      <Header
        title="Add Candidates"
        sub={data ? `${data.count} actionable · Avoid excluded · threshold ${data.threshold}` : undefined}
      />
      <div className="page-content">
        {loading && <Spinner />}
        {error && <ErrorMessage message={error} />}
        {data && data.count === 0 && (
          <div style={{ color: 'var(--text-muted)', padding: '40px 0' }}>
            No actionable add candidates at this time.
          </div>
        )}
        {data && data.candidates.map(c => {
          const expl = c.position.add_explanation
          return (
            <div key={c.ticker} className="pos-card" style={{ marginBottom: 12 }}>
              <div className="pos-card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Link to={`/positions/${c.ticker}`} className="pos-ticker"
                    style={{ color: 'var(--text)' }}>
                    {c.ticker}
                  </Link>
                  <span className={`badge ${actionBadgeClass(c.action)}`}>{c.action}</span>
                  <span className={`badge ${opportunityBadgeClass(c.opportunity_type)}`}>
                    {c.opportunity_type}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <span style={{ fontSize: 22, fontWeight: 700, color: addColor(c.add_score) }}>
                    {c.add_score.toFixed(1)}
                  </span>
                  <Link to={`/positions/${c.ticker}`} style={{ fontSize: 12, color: 'var(--accent)' }}>
                    Detail →
                  </Link>
                </div>
              </div>

              <div className="grid-3" style={{ marginBottom: expl ? 14 : 0 }}>
                <div>
                  <ScoreBar label="add score" score={c.position.add.score}
                    color={addColor(c.position.add.score)} />
                  <ScoreBar label="upside" score={c.position.upside.score}
                    color={addColor(c.position.upside.score)} />
                </div>
                <div>
                  <ScoreBar label="recovery" score={c.position.recovery.score}
                    color={addColor(c.position.recovery.score)} />
                  <ScoreBar label="setup integrity" score={c.position.setup_integrity.score}
                    color={scoreColor(c.position.setup_integrity.score)} />
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', paddingTop: 4 }}>
                  <div>Driver: <span style={{ color: 'var(--text)' }}>{c.primary_driver}</span></div>
                  <div style={{ marginTop: 4 }}>Strength: <span style={{ color: 'var(--text)' }}>
                    {c.position.strength.score.toFixed(1)}
                  </span></div>
                  {c.position.add.guardrail_1_applied && (
                    <div style={{ marginTop: 4, color: 'var(--orange)' }}>GR1: strength cap applied</div>
                  )}
                  {c.position.add.guardrail_2_applied && (
                    <div style={{ marginTop: 4, color: 'var(--red)' }}>GR2: broken trend cap applied</div>
                  )}
                </div>
              </div>

              {expl && (
                <div className="explanation-box add">
                  <div className="explanation-action">
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {expl.confidence} confidence
                    </span>
                  </div>
                  <div className="explanation-narrative" style={{ marginTop: 6 }}>
                    {expl.narrative}
                  </div>
                  <ul className="explanation-inval">
                    {expl.invalidation_conditions.map((cond, i) => (
                      <li key={i}>{cond}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </>
  )
}
