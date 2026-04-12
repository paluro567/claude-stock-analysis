import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Header } from '../components/layout/Header'
import { Spinner, ErrorMessage } from '../components/common/Spinner'
import { trimColor, addColor, scoreColor, flagBadgeClass, flagLabel } from '../utils/scores'

export function ReviewQueue() {
  const { data, loading, error } = useApi(api.getReviewQueue)

  return (
    <>
      <Header
        title="Review Queue"
        sub={data ? `${data.count} positions flagged` : undefined}
      />
      <div className="page-content">
        {loading && <Spinner />}
        {error && <ErrorMessage message={error} />}
        {data && data.count === 0 && (
          <div style={{ color: 'var(--text-muted)', padding: '40px 0' }}>
            No positions in the review queue.
          </div>
        )}
        {data && data.count > 0 && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {data.queue.map(q => (
              <div key={q.ticker} className="queue-row">
                <Link to={`/positions/${q.ticker}`} className="queue-ticker"
                  style={{ color: 'var(--text)' }}>
                  {q.ticker}
                </Link>

                <div className="queue-scores">
                  <div className="queue-score-item">
                    <span className="queue-score-label">Trim</span>
                    <span className="queue-score-val" style={{ color: trimColor(q.trim_score) }}>
                      {q.trim_score.toFixed(1)}
                    </span>
                  </div>
                  <div className="queue-score-item">
                    <span className="queue-score-label">Add</span>
                    <span className="queue-score-val" style={{ color: addColor(q.add_score) }}>
                      {q.add_score.toFixed(1)}
                    </span>
                  </div>
                  <div className="queue-score-item">
                    <span className="queue-score-label">Str</span>
                    <span className="queue-score-val" style={{ color: scoreColor(q.strength_score) }}>
                      {q.strength_score.toFixed(1)}
                    </span>
                  </div>
                  <div className="queue-score-item">
                    <span className="queue-score-label">Risk</span>
                    <span className="queue-score-val" style={{ color: trimColor(q.risk_score) }}>
                      {q.risk_score.toFixed(1)}
                    </span>
                  </div>
                  <div className="queue-score-item">
                    <span className="queue-score-label">Exp</span>
                    <span className="queue-score-val" style={{ color: trimColor(q.exposure_score) }}>
                      {q.exposure_score.toFixed(1)}
                    </span>
                  </div>
                </div>

                <div className="queue-flags">
                  {q.flags.map(f => (
                    <span key={f} className={`badge ${flagBadgeClass(f)}`}>
                      {flagLabel(f)}
                    </span>
                  ))}
                </div>

                <Link to={`/positions/${q.ticker}`}
                  style={{ fontSize: 12, color: 'var(--accent)', flexShrink: 0 }}>
                  Detail →
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
