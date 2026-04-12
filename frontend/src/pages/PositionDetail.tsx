import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { Header } from '../components/layout/Header'
import { Spinner, ErrorMessage } from '../components/common/Spinner'
import { PositionScores } from '../components/common/PositionScores'

export function PositionDetail() {
  const { ticker = '' } = useParams<{ ticker: string }>()
  const { data, loading, error } = useApi(() => api.getPosition(ticker))

  const weight = (data?.exposure.components.size_score?.['weight'] as number | undefined) ?? 0

  return (
    <>
      <Header
        title={ticker.toUpperCase()}
        sub={data ? `${(weight * 100).toFixed(1)}% of portfolio · as of ${data.as_of}` : undefined}
      />
      <div className="page-content">
        <div style={{ marginBottom: 16 }}>
          <Link to="/positions" style={{ fontSize: 13, color: 'var(--accent)' }}>
            ← Back to Positions
          </Link>
        </div>

        {loading && <Spinner />}
        {error && (
          <ErrorMessage
            message={error.includes('404') ? `${ticker.toUpperCase()} is not in the portfolio.` : error}
          />
        )}
        {data && <PositionScores position={data} />}
      </div>
    </>
  )
}
