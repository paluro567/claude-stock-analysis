import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Header } from '../components/layout/Header'
import { Spinner, ErrorMessage } from '../components/common/Spinner'
import { ScoreBar } from '../components/common/ScoreBar'
import { trimColor, scoreColor, actionBadgeClass } from '../utils/scores'

export function TrimWatchlist() {
  const { data, loading, error } = useApi(api.getTrimCandidates)

  return (
    <>
      <Header
        title="Trim Watchlist"
        sub={data ? `${data.count} candidates · threshold ${data.threshold}` : undefined}
      />
      <div className="page-content">
        {loading && <Spinner />}
        {error && <ErrorMessage message={error} />}
        {data && data.count === 0 && (
          <div style={{ color: 'var(--text-muted)', padding: '40px 0' }}>
            No trim candidates at this time.
          </div>
        )}
        {data && data.candidates.map(c => {
          const expl = c.position.trim_explanation
          return (
            <div key={c.ticker} className="pos-card" style={{ marginBottom: 12 }}>
              <div className="pos-card-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Link to={`/positions/${c.ticker}`} className="pos-ticker"
                    style={{ color: 'var(--text)' }}>
                    {c.ticker}
                  </Link>
                  <span className={`badge ${actionBadgeClass(c.action)}`}>{c.action}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <span style={{ fontSize: 22, fontWeight: 700, color: trimColor(c.trim_score) }}>
                    {c.trim_score.toFixed(1)}
                  </span>
                  <Link to={`/positions/${c.ticker}`} style={{ fontSize: 12, color: 'var(--accent)' }}>
                    Detail →
                  </Link>
                </div>
              </div>

              <div className="grid-3" style={{ marginBottom: expl ? 14 : 0 }}>
                <div>
                  <ScoreBar label="trim score" score={c.position.trim.score}
                    color={trimColor(c.position.trim.score)} />
                  <ScoreBar label="risk score" score={c.position.risk.score}
                    color={trimColor(c.position.risk.score)} />
                </div>
                <div>
                  <ScoreBar label="exposure" score={c.position.exposure.score}
                    color={trimColor(c.position.exposure.score)} />
                  <ScoreBar label="strength" score={c.position.strength.score}
                    color={scoreColor(c.position.strength.score)} />
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', paddingTop: 4 }}>
                  <div>Driver: <span style={{ color: 'var(--text)' }}>{c.primary_driver}</span></div>
                  <div style={{ marginTop: 4 }}>
                    Risk type: <span style={{ color: 'var(--text)' }}>{c.risk_type}</span>
                  </div>
                </div>
              </div>

              {expl && (
                <div className="explanation-box trim">
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
