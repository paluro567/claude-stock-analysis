import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'

const STOCK_COLORS = ['#5c6bc0', '#14b8a6', '#f59e0b']
const STOCK_LABELS = ['Stock A', 'Stock B', 'Stock C']

function fmt(v) {
  return v != null ? v.toFixed(1) : null
}

function TickerSlot({ index, value, onChange, data, loading, error }) {
  const [input, setInput] = useState(value || '')
  const color = STOCK_COLORS[index]

  const handleSubmit = (e) => {
    e.preventDefault()
    const upper = input.trim().toUpperCase()
    if (upper) onChange(upper)
  }

  return (
    <div className="compare-slot" style={{ borderTop: `3px solid ${color}` }}>
      <div className="compare-slot-label" style={{ color }}>Stock {index + 1}</div>
      <form onSubmit={handleSubmit} className="compare-slot-form">
        <input
          value={input}
          onChange={e => setInput(e.target.value.toUpperCase())}
          placeholder="Enter ticker..."
          className="compare-input"
        />
        <button type="submit" className="compare-btn" style={{ background: color }}>Go</button>
        {value && (
          <button type="button" className="compare-clear-btn" onClick={() => { setInput(''); onChange(null) }}>✕</button>
        )}
      </form>
      {loading && <div className="compare-slot-status">Loading…</div>}
      {error && <div className="compare-slot-status error">{error}</div>}
      {data && !loading && (
        <div className="compare-slot-name">{data.name} <span style={{ color: '#6b7280', fontSize: '0.75rem' }}>({data.ticker})</span></div>
      )}
    </div>
  )
}

function OvervaluationBar({ data, color }) {
  if (!data) return null

  const { trailingPE, sectorPE, ticker, name } = data

  if (trailingPE == null || sectorPE == null) {
    return (
      <div className="ovval-card" style={{ borderLeft: `4px solid ${color}` }}>
        <div className="ovval-ticker">{ticker}</div>
        <div className="ovval-na">Overvaluation data unavailable</div>
      </div>
    )
  }

  // pct above/below sector average — clamped to [-60, +120] → mapped to 0-100%
  const rawPct = ((trailingPE - sectorPE) / sectorPE) * 100
  const clampMin = -60
  const clampMax = 120
  const position = Math.min(100, Math.max(0, ((rawPct - clampMin) / (clampMax - clampMin)) * 100))

  const label = rawPct > 0
    ? `+${rawPct.toFixed(1)}% above sector avg`
    : `${rawPct.toFixed(1)}% below sector avg`

  const sentiment =
    rawPct > 60 ? 'Very Overvalued' :
    rawPct > 20 ? 'Overvalued' :
    rawPct > -20 ? 'Fairly Valued' :
    rawPct > -40 ? 'Undervalued' : 'Deeply Undervalued'

  const sentimentColor =
    rawPct > 60 ? '#ef4444' :
    rawPct > 20 ? '#f97316' :
    rawPct > -20 ? '#eab308' :
    rawPct > -40 ? '#86efac' : '#22c55e'

  return (
    <div className="ovval-card" style={{ borderLeft: `4px solid ${color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.4rem' }}>
        <div className="ovval-ticker">{ticker} <span style={{ fontWeight: 400, fontSize: '0.8rem', color: '#9ca3af' }}>{name}</span></div>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: sentimentColor }}>{sentiment}</div>
      </div>
      <div className="ovval-bar-track">
        <div className="ovval-bar-fill" />
        <div className="ovval-marker" style={{ left: `${position}%` }} />
      </div>
      <div className="ovval-bar-labels">
        <span style={{ color: '#22c55e' }}>Undervalued</span>
        <span style={{ color: '#eab308' }}>Fair</span>
        <span style={{ color: '#ef4444' }}>Overvalued</span>
      </div>
      <div style={{ marginTop: '0.5rem', fontSize: '0.78rem', color: '#9ca3af' }}>
        TTM PE <strong style={{ color: '#e0e0e0' }}>{fmt(trailingPE)}</strong>
        &nbsp;·&nbsp; Sector Avg <strong style={{ color: '#e0e0e0' }}>{fmt(sectorPE)}</strong>
        &nbsp;·&nbsp; <span style={{ color: sentimentColor }}>{label}</span>
      </div>
    </div>
  )
}

function ComparePage() {
  const [tickers, setTickers] = useState([null, null, null])
  const [stocks, setStocks] = useState([null, null, null])
  const [loadings, setLoadings] = useState([false, false, false])
  const [errors, setErrors] = useState([null, null, null])

  const setTicker = (index, ticker) => {
    setTickers(prev => { const n = [...prev]; n[index] = ticker; return n })
    if (!ticker) {
      setStocks(prev => { const n = [...prev]; n[index] = null; return n })
      setErrors(prev => { const n = [...prev]; n[index] = null; return n })
    }
  }

  useEffect(() => {
    tickers.forEach((ticker, i) => {
      if (!ticker) return
      setLoadings(prev => { const n = [...prev]; n[i] = true; return n })
      setErrors(prev => { const n = [...prev]; n[i] = null; return n })
      axios.get(`/api/stock/${ticker}`)
        .then(res => {
          setStocks(prev => { const n = [...prev]; n[i] = res.data; return n })
          setLoadings(prev => { const n = [...prev]; n[i] = false; return n })
        })
        .catch(err => {
          setErrors(prev => { const n = [...prev]; n[i] = err.response?.data?.detail || 'Failed to load'; return n })
          setStocks(prev => { const n = [...prev]; n[i] = null; return n })
          setLoadings(prev => { const n = [...prev]; n[i] = false; return n })
        })
    })
  }, [tickers.join(',')])

  const activeStocks = stocks.filter(Boolean)

  // Build grouped chart data
  const chartData = [
    { metric: 'TTM PE' },
    { metric: 'Forward PE' },
    { metric: '2yr Forward PE' },
  ]

  stocks.forEach((s, i) => {
    if (!s) return
    chartData[0][s.ticker] = s.trailingPE
    chartData[1][s.ticker] = s.forwardPE
    chartData[2][s.ticker] = s.twoYearForwardPE
  })

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: '#232635', border: '1px solid #2a2d3a', borderRadius: 6, padding: '8px 12px', fontSize: '0.8rem' }}>
          <div style={{ color: '#9ca3af', marginBottom: 4 }}>{label}</div>
          {payload.map((p, i) => (
            <div key={i} style={{ color: p.fill, marginBottom: 2 }}>
              {p.dataKey}: <strong>{p.value != null ? p.value.toFixed(1) : 'N/A'}</strong>
            </div>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="compare-page">
      <div className="compare-slots-row">
        {[0, 1, 2].map(i => (
          <TickerSlot
            key={i}
            index={i}
            value={tickers[i]}
            onChange={(t) => setTicker(i, t)}
            data={stocks[i]}
            loading={loadings[i]}
            error={errors[i]}
          />
        ))}
      </div>

      {activeStocks.length > 0 && (
        <>
          <div className="panel">
            <div className="pe-section-title">PE Comparison</div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 4 }} barGap={4} barCategoryGap="28%">
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" vertical={false} />
                <XAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Legend wrapperStyle={{ fontSize: '0.8rem', color: '#9ca3af', paddingTop: '0.5rem' }} />
                {stocks.map((s, i) => s && (
                  <Bar key={s.ticker} dataKey={s.ticker} fill={STOCK_COLORS[i]} radius={[4, 4, 0, 0]} maxBarSize={60} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="panel">
            <div className="pe-section-title">Valuation vs Sector</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {stocks.map((s, i) => s && (
                <OvervaluationBar key={s.ticker} data={s} color={STOCK_COLORS[i]} />
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="pe-section-title">Side-by-Side Metrics</div>
            <div className="compare-metrics-grid">
              <div className="compare-metrics-header">
                <div />
                {stocks.map((s, i) => s && (
                  <div key={i} style={{ color: STOCK_COLORS[i], fontWeight: 700 }}>{s.ticker}</div>
                ))}
              </div>
              {[
                { label: 'TTM PE', key: 'trailingPE' },
                { label: 'Forward PE', key: 'forwardPE' },
                { label: '2yr Forward PE', key: 'twoYearForwardPE' },
                { label: 'Sector Avg PE', key: 'sectorPE' },
                { label: 'Sector', key: 'sector' },
                { label: 'Industry', key: 'industry' },
              ].map(row => (
                <div key={row.label} className="compare-metrics-row">
                  <div className="compare-metrics-label">{row.label}</div>
                  {stocks.map((s, i) => (
                    <div key={i} className="compare-metrics-value">
                      {s ? (s[row.key] != null ? (typeof s[row.key] === 'number' ? s[row.key].toFixed(1) : s[row.key]) : 'N/A') : '—'}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeStocks.length === 0 && (
        <div className="empty-state">Enter up to 3 tickers above to compare.</div>
      )}
    </div>
  )
}

export default ComparePage
