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
} from 'recharts'
import { cacheGet, cacheSet } from '../utils/stockCache'

const STOCK_COLORS = ['#5c6bc0', '#14b8a6', '#f59e0b']

const METRICS = [
  // Valuation
  { key: 'trailingPE',              label: 'P/E (TTM)',             category: 'Valuation',     lowerBetter: true,  pct: false },
  { key: 'forwardPE',               label: 'Forward P/E',           category: 'Valuation',     lowerBetter: true,  pct: false },
  { key: 'pegRatio',                label: 'PEG Ratio',             category: 'Valuation',     lowerBetter: true,  pct: false },
  // Growth
  { key: 'revenueGrowth',           label: 'Revenue Growth',        category: 'Growth',        lowerBetter: false, pct: true  },
  { key: 'earningsGrowth',          label: 'EPS Growth',            category: 'Growth',        lowerBetter: false, pct: true  },
  { key: 'fcfGrowth',               label: 'FCF Growth',            category: 'Growth',        lowerBetter: false, pct: true  },
  // Profitability
  { key: 'grossMargins',            label: 'Gross Margin',          category: 'Profitability', lowerBetter: false, pct: true  },
  { key: 'operatingMargins',        label: 'Operating Margin',      category: 'Profitability', lowerBetter: false, pct: true  },
  { key: 'returnOnEquity',          label: 'ROE',                   category: 'Profitability', lowerBetter: false, pct: true  },
  // Balance Sheet
  { key: 'debtToEquity',            label: 'Debt / Equity',         category: 'Balance Sheet', lowerBetter: true,  pct: false },
  { key: 'currentRatio',            label: 'Current Ratio',         category: 'Balance Sheet', lowerBetter: false, pct: false },
  // Momentum
  { key: 'relativeStrength',        label: 'Rel. Strength vs S&P',  category: 'Momentum',      lowerBetter: false, pct: true  },
  { key: 'heldPercentInstitutions', label: 'Institutional Own.',    category: 'Momentum',      lowerBetter: false, pct: true  },
  { key: 'volumeTrend',             label: 'Volume Trend',          category: 'Momentum',      lowerBetter: false, pct: true  },
]

const CATEGORIES = ['Valuation', 'Growth', 'Profitability', 'Balance Sheet', 'Momentum']

function rankColor(allValues, value, lowerBetter) {
  if (value == null) return 'transparent'
  const valid = allValues.filter(v => v != null).sort((a, b) => a - b)
  if (valid.length < 2) return 'transparent'
  const idx = valid.findIndex(v => Math.abs(v - value) < 1e-9)
  const pct = idx / (valid.length - 1) // 0=lowest, 1=highest
  const score = lowerBetter ? 1 - pct : pct
  if (score >= 0.6) return 'rgba(34,197,94,0.2)'
  if (score >= 0.33) return 'rgba(234,179,8,0.18)'
  return 'rgba(239,68,68,0.2)'
}

function fmtVal(value, pct) {
  if (value == null) return '—'
  if (pct) return `${(value * 100).toFixed(1)}%`
  return Number(value).toFixed(value > 100 ? 0 : value > 10 ? 1 : 2)
}

function fmt(v) {
  return v != null ? v.toFixed(1) : null
}

function MetricsTable({ stocksData, tickers, colors }) {
  return (
    <div className="metrics-table-wrap">
      <table className="metrics-table">
        <thead>
          <tr>
            <th>Metric</th>
            {tickers.map((t, i) => (
              <th key={t}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  {colors && colors[i] && (
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: colors[i], display: 'inline-block' }} />
                  )}
                  {t}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {CATEGORIES.map(cat => {
            const catMetrics = METRICS.filter(m => m.category === cat)
            return [
              <tr key={`cat-${cat}`} className="category-row">
                <td colSpan={tickers.length + 1}>{cat}</td>
              </tr>,
              ...catMetrics.map(metric => {
                const allValues = stocksData.map(s => s ? s[metric.key] : null)
                return (
                  <tr key={metric.key}>
                    <td>{metric.label}</td>
                    {stocksData.map((s, i) => {
                      const val = s ? s[metric.key] : null
                      const bg = rankColor(allValues, val, metric.lowerBetter)
                      return (
                        <td
                          key={tickers[i]}
                          style={{
                            background: bg,
                            color: val == null ? '#4b5563' : '#e0e0e0',
                          }}
                        >
                          {fmtVal(val, metric.pct)}
                        </td>
                      )
                    })}
                  </tr>
                )
              }),
            ]
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── Overview Tab ────────────────────────────────────────────────────────────

function OverviewTab({ positions }) {
  const [loaded, setLoaded] = useState([])

  useEffect(() => {
    let cancelled = false
    async function fetchAll() {
      for (let i = 0; i < positions.length; i++) {
        if (cancelled) break
        const t = positions[i]
        if (!cacheGet(t)) {
          try {
            const res = await axios.get(`/api/stock/${t}`)
            cacheSet(t, res.data)
          } catch (e) {}
          await new Promise(r => setTimeout(r, 300))
        }
        if (!cancelled) setLoaded(prev => [...new Set([...prev, t])])
      }
    }
    setLoaded([])
    fetchAll()
    return () => { cancelled = true }
  }, [positions.join(',')])

  const stocksData = loaded.map(t => cacheGet(t))
  const total = positions.length
  const done = loaded.length
  const progress = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div>
      {done < total && (
        <div>
          <div className="compare-loading">Loading {done} / {total} tickers…</div>
          <div className="compare-progress">
            <div className="compare-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
      {stocksData.length > 0 && (
        <MetricsTable
          stocksData={stocksData}
          tickers={loaded}
          colors={null}
        />
      )}
      {stocksData.length === 0 && done === total && total === 0 && (
        <div className="empty-state">No positions in portfolio.</div>
      )}
    </div>
  )
}

// ─── Ticker Slot ─────────────────────────────────────────────────────────────

function TickerSlot({ index, value, onChange, data, loading, error }) {
  const [input, setInput] = useState(value || '')
  const color = STOCK_COLORS[index]

  const handleSubmit = (e) => {
    e.preventDefault()
    const upper = input.trim().toUpperCase()
    if (upper) onChange(upper)
  }

  const handleClear = () => { setInput(''); onChange(null) }

  return (
    <div className="compare-slot" style={{ borderTop: `3px solid ${color}` }}>
      <div className="compare-slot-label" style={{ color }}>Stock {index + 1}</div>

      {/* Show loaded stock prominently, hide input form */}
      {data && !loading ? (
        <div className="compare-slot-loaded">
          <div className="compare-slot-loaded-info">
            <span className="compare-slot-ticker" style={{ color }}>{data.ticker}</span>
            <span className="compare-slot-fullname">{data.name}</span>
          </div>
          <button className="compare-slot-remove" onClick={handleClear} title="Remove">✕</button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="compare-slot-form">
          <input
            value={input}
            onChange={e => setInput(e.target.value.toUpperCase())}
            placeholder="Enter ticker..."
            className="compare-input"
          />
          <button type="submit" className="compare-btn" style={{ background: color }}>Go</button>
        </form>
      )}

      {loading && <div className="compare-slot-status">Loading…</div>}
      {error && (
        <div className="compare-slot-status error" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{error}</span>
          <button className="compare-slot-remove" onClick={handleClear} title="Clear">✕</button>
        </div>
      )}
    </div>
  )
}

// ─── Overvaluation Bar ───────────────────────────────────────────────────────

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

// ─── Custom Tooltip ──────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div style={{ background: '#232635', border: '1px solid #2a2d3a', borderRadius: 6, padding: '8px 12px', fontSize: '0.8rem' }}>
        <div style={{ color: '#9ca3af', marginBottom: 4 }}>{label}</div>
        {payload.map((p, i) => (
          <div key={i} style={{ color: p.fill, marginBottom: 2 }}>
            {p.dataKey}: <strong>{p.value != null ? p.value.toFixed(2) : 'N/A'}</strong>
          </div>
        ))}
      </div>
    )
  }
  return null
}

// ─── Detail Tab ──────────────────────────────────────────────────────────────

function DetailTab() {
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
  const activeTickers = tickers.filter((t, i) => stocks[i] != null)
  const activeStocksData = stocks.filter(Boolean)
  const activeColors = stocks.map((s, i) => s ? STOCK_COLORS[i] : null).filter(Boolean)

  // Build per-category bar charts
  const categoryCharts = CATEGORIES.map(cat => {
    const catMetrics = METRICS.filter(m => m.category === cat)
    // Filter metrics where at least one stock has a non-null value
    const validMetrics = catMetrics.filter(m =>
      stocks.some(s => s != null && s[m.key] != null)
    )
    if (validMetrics.length === 0) return null

    const chartData = validMetrics.map(m => {
      const entry = { metric: m.label }
      stocks.forEach((s, i) => {
        if (s != null && s[m.key] != null) {
          entry[s.ticker] = m.pct ? s[m.key] * 100 : s[m.key]
        }
      })
      return entry
    })

    return { cat, chartData, validMetrics }
  }).filter(Boolean)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
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
            <div className="pe-section-title">Metrics Comparison</div>
            <MetricsTable
              stocksData={stocks}
              tickers={tickers.map((t, i) => stocks[i] ? t : null).filter(Boolean)}
              colors={stocks.map((s, i) => s ? STOCK_COLORS[i] : null).filter(Boolean)}
            />
          </div>

          <div className="panel">
            <div className="pe-section-title">Valuation vs Sector</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {stocks.map((s, i) => s && (
                <OvervaluationBar key={s.ticker} data={s} color={STOCK_COLORS[i]} />
              ))}
            </div>
          </div>

          {categoryCharts.map(({ cat, chartData }) => (
            <div key={cat} className="panel">
              <div className="pe-section-title">{cat}</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 4 }} barGap={4} barCategoryGap="28%">
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" vertical={false} />
                  <XAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  <Legend wrapperStyle={{ fontSize: '0.8rem', color: '#9ca3af', paddingTop: '0.5rem' }} />
                  {stocks.map((s, i) => s && (
                    <Bar key={s.ticker} dataKey={s.ticker} fill={STOCK_COLORS[i]} radius={[4, 4, 0, 0]} maxBarSize={60} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          ))}
        </>
      )}

      {activeStocks.length === 0 && (
        <div className="empty-state">Enter up to 3 tickers above to compare.</div>
      )}
    </div>
  )
}

// ─── ComparePage ─────────────────────────────────────────────────────────────

function ComparePage({ positions }) {
  const [subTab, setSubTab] = useState('overview')

  return (
    <div className="compare-page">
      {/* Sub-tab toggle */}
      <div className="compare-subtabs">
        <button
          className={`compare-subtab ${subTab === 'overview' ? 'active' : ''}`}
          onClick={() => setSubTab('overview')}
        >
          Portfolio Overview
        </button>
        <button
          className={`compare-subtab ${subTab === 'detail' ? 'active' : ''}`}
          onClick={() => setSubTab('detail')}
        >
          Detail Compare
        </button>
      </div>

      {subTab === 'overview' && <OverviewTab positions={positions || []} />}
      {subTab === 'detail' && <DetailTab />}
    </div>
  )
}

export default ComparePage
