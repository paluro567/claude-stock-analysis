import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Header } from '../components/layout/Header'
import { Spinner, ErrorMessage } from '../components/common/Spinner'
import { ScoreBar } from '../components/common/ScoreBar'

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function hhiLabel(hhi: number) {
  if (hhi > 2500) return { text: 'High', color: 'var(--red)' }
  if (hhi > 1500) return { text: 'Moderate', color: 'var(--yellow)' }
  return { text: 'Low', color: 'var(--green)' }
}

export function Overview() {
  const { data, loading, error } = useApi(api.getPortfolioSummary)

  return (
    <>
      <Header title="Overview" sub={data ? `as of ${new Date().toLocaleDateString()}` : undefined} />
      <div className="page-content">
        {loading && <Spinner />}
        {error && <ErrorMessage message={error} />}
        {data && (
          <>
            {/* Summary cards */}
            <div className="grid-4" style={{ marginBottom: 24 }}>
              <div className="card">
                <div className="card-title">Total Value</div>
                <div className="card-value">{fmt(data.summary.total_value)}</div>
                <div className="card-sub">{data.summary.position_count} positions</div>
              </div>

              <div className="card">
                <div className="card-title">Concentration HHI</div>
                <div className="card-value" style={{ color: hhiLabel(data.summary.concentration_hhi).color }}>
                  {data.summary.concentration_hhi.toFixed(0)}
                </div>
                <div className="card-sub">{hhiLabel(data.summary.concentration_hhi).text} concentration</div>
              </div>

              <div className="card">
                <div className="card-title">Trim Candidates</div>
                <div className="card-value" style={{ color: data.trim_candidate_count > 0 ? 'var(--red)' : 'var(--text)' }}>
                  {data.trim_candidate_count}
                </div>
                <div className="card-sub">score ≥ 25</div>
              </div>

              <div className="card">
                <div className="card-title">Add Candidates</div>
                <div className="card-value" style={{ color: data.add_candidate_count > 0 ? 'var(--green)' : 'var(--text)' }}>
                  {data.add_candidate_count}
                </div>
                <div className="card-sub">actionable (non-Avoid)</div>
              </div>
            </div>

            <div className="grid-2">
              {/* Top positions */}
              <div>
                <div className="section-title">Top Positions</div>
                <div className="card" style={{ padding: '8px 20px' }}>
                  {data.summary.top_positions.map(p => (
                    <div key={p.ticker} className="top-pos-row">
                      <span style={{ fontWeight: 700, width: 60 }}>{p.ticker}</span>
                      <div style={{ flex: 1, padding: '0 16px' }}>
                        <div style={{
                          height: 6,
                          background: 'var(--surface2)',
                          borderRadius: 99,
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            height: '100%',
                            width: `${p.weight * 100}%`,
                            background: 'var(--accent)',
                            borderRadius: 99,
                          }} />
                        </div>
                      </div>
                      <span style={{ color: 'var(--text-muted)', width: 44, textAlign: 'right' }}>
                        {(p.weight * 100).toFixed(1)}%
                      </span>
                      <span style={{ width: 90, textAlign: 'right' }}>{fmt(p.value)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cluster exposures */}
              <div>
                <div className="section-title">Cluster Exposures</div>
                <div className="card" style={{ padding: '8px 20px' }}>
                  {Object.entries(data.cluster_exposures).map(([name, exp]) => (
                    <div key={name} className="cluster-row">
                      <span className="cluster-name">{name}</span>
                      <div className="cluster-bar-wrap">
                        <div style={{
                          height: 6,
                          background: 'var(--surface2)',
                          borderRadius: 99,
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            height: '100%',
                            width: `${exp.total_weight * 100}%`,
                            background: exp.total_weight > 0.50 ? 'var(--red)' : exp.total_weight > 0.25 ? 'var(--orange)' : 'var(--accent)',
                            borderRadius: 99,
                          }} />
                        </div>
                      </div>
                      <span className="cluster-weight">{(exp.total_weight * 100).toFixed(1)}%</span>
                      <span className="cluster-tickers">[{exp.tickers.join(', ')}]</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Asset type */}
            <div className="section-title" style={{ marginTop: 24 }}>Asset Types</div>
            <div className="grid-3">
              {Object.entries(data.summary.asset_type_counts).map(([type, count]) => (
                <div key={type} className="card">
                  <div className="card-title">{type}</div>
                  <div className="card-value">{count}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  )
}
