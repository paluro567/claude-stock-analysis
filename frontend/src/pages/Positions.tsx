import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Header } from '../components/layout/Header'
import { Spinner, ErrorMessage } from '../components/common/Spinner'
import { ScoreBar } from '../components/common/ScoreBar'
import { scoreColor, trimColor, addColor, actionBadgeClass } from '../utils/scores'

export function Positions() {
  const { data, loading, error } = useApi(api.getPositions)

  return (
    <>
      <Header title="Positions" sub={data ? `${data.length} total` : undefined} />
      <div className="page-content">
        {loading && <Spinner />}
        {error && <ErrorMessage message={error} />}
        {data && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {data.map(pos => {
              const trimExpl = pos.trim_explanation
              const addExpl  = pos.add_explanation
              const weight   = (pos.exposure.components.size_score?.['weight'] as number | undefined) ?? 0
              return (
                <div key={pos.ticker} className="pos-card">
                  <div className="pos-card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <Link
                        to={`/positions/${pos.ticker}`}
                        className="pos-ticker"
                        style={{ color: 'var(--text)' }}
                      >
                        {pos.ticker}
                      </Link>
                      <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                        {(weight * 100).toFixed(1)}% of portfolio
                      </span>
                      {pos.data_quality.level !== 'none' && (
                        <span className={`dq-tag dq-${pos.data_quality.level}`}>
                          {pos.data_quality.level}
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                      {trimExpl && (
                        <span className={`badge ${actionBadgeClass(trimExpl.action_label)}`}>
                          {trimExpl.action_label}
                        </span>
                      )}
                      {addExpl && (
                        <span className={`badge ${actionBadgeClass(addExpl.action_label)}`}>
                          {addExpl.action_label}
                        </span>
                      )}
                      <Link
                        to={`/positions/${pos.ticker}`}
                        style={{ fontSize: 12, color: 'var(--accent)' }}
                      >
                        Detail →
                      </Link>
                    </div>
                  </div>

                  <div className="grid-3">
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8,
                        textTransform: 'uppercase', letterSpacing: '0.06em' }}>Strength</div>
                      <ScoreBar label="strength" score={pos.strength.score}
                        color={scoreColor(pos.strength.score)} />
                      <ScoreBar label="risk" score={pos.risk.score}
                        color={trimColor(pos.risk.score)} />
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8,
                        textTransform: 'uppercase', letterSpacing: '0.06em' }}>Add / Trim</div>
                      <ScoreBar label="add" score={pos.add.score}
                        color={addColor(pos.add.score)} />
                      <ScoreBar label="trim" score={pos.trim.score}
                        color={trimColor(pos.trim.score)} />
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8,
                        textTransform: 'uppercase', letterSpacing: '0.06em' }}>Exposure</div>
                      <ScoreBar label="exposure" score={pos.exposure.score}
                        color={trimColor(pos.exposure.score)} />
                      <ScoreBar label="setup integrity" score={pos.setup_integrity.score}
                        color={scoreColor(pos.setup_integrity.score)} />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
