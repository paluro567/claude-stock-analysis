import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import axios from 'axios'
import { cacheGet, cacheSet } from '../utils/stockCache'

function fmt(v, d = 1) { return v != null ? Number(v).toFixed(d) : 'N/A' }
function fmtPrice(v) { return v != null ? `$${Number(v).toFixed(2)}` : 'N/A' }
function fmtCap(v) {
  if (v == null) return 'N/A'
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  return `$${(v / 1e6).toFixed(0)}M`
}

function OvervaluationBar({ pct }) {
  if (pct == null) return null
  const clampMin = -60, clampMax = 120
  const position = Math.min(100, Math.max(0, ((pct - clampMin) / (clampMax - clampMin)) * 100))
  const sentiment =
    pct > 60 ? 'Very Overvalued' :
    pct > 20 ? 'Overvalued' :
    pct > -20 ? 'Fairly Valued' :
    pct > -40 ? 'Undervalued' : 'Deeply Undervalued'
  const color =
    pct > 60 ? '#ef4444' : pct > 20 ? '#f97316' : pct > -20 ? '#eab308' : '#22c55e'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.78rem', color: '#9ca3af' }}>
          {pct > 0 ? '+' : ''}{pct}% vs sector avg
        </span>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color }}>{sentiment}</span>
      </div>
      <div className="ovval-bar-track">
        <div className="ovval-marker" style={{ left: `${position}%` }} />
      </div>
      <div className="ovval-bar-labels">
        <span style={{ color: '#22c55e' }}>Undervalued</span>
        <span style={{ color: '#eab308' }}>Fair</span>
        <span style={{ color: '#ef4444' }}>Overvalued</span>
      </div>
    </div>
  )
}

const BarTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: '#232635', border: '1px solid #2a2d3a', borderRadius: 6, padding: '6px 10px', fontSize: '0.78rem' }}>
        <div style={{ color: '#9ca3af', marginBottom: 2 }}>{label}</div>
        <div style={{ color: '#e0e0e0' }}>PE: <strong>{payload[0]?.value?.toFixed(1) ?? 'N/A'}</strong></div>
      </div>
    )
  }
  return null
}

function StockDetail({ ticker }) {
  const [data, setData] = useState(null)
  const [peers, setPeers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const cached = cacheGet(ticker)
    if (cached) { setData(cached); setLoading(false) }
    else {
      setLoading(true); setError(null); setData(null)
      axios.get(`/api/stock/${ticker}`)
        .then(res => { cacheSet(ticker, res.data); setData(res.data); setLoading(false) })
        .catch(err => { setError(err.response?.data?.detail || err.message); setLoading(false) })
    }
  }, [ticker])

  useEffect(() => {
    setPeers([])
    const key = `${ticker}:peers`
    const cached = cacheGet(key)
    if (cached) { setPeers(cached.peers || []); return }
    axios.get(`/api/stock/${ticker}/peers`)
      .then(res => { cacheSet(key, res.data); setPeers(res.data.peers || []) })
      .catch(() => setPeers([]))
  }, [ticker])

  if (loading) return <div className="panel"><div className="loading-state">Loading {ticker}…</div></div>
  if (error) return <div className="panel"><div className="error-state">Error: {error}</div></div>

  const priceChange = data.currentPrice != null && data.previousClose != null
    ? data.currentPrice - data.previousClose : null
  const pctChange = priceChange != null && data.previousClose
    ? (priceChange / data.previousClose) * 100 : null
  const isUp = priceChange != null ? priceChange >= 0 : null

  // Bar chart data
  const barData = []
  if (data.trailingPE != null) barData.push({ name: ticker, pe: data.trailingPE, type: 'current' })
  if (data.sectorPE != null) barData.push({ name: 'Sector Avg', pe: data.sectorPE, type: 'sector' })
  for (const p of peers) {
    if (p.trailingPE != null) barData.push({ name: p.ticker, pe: p.trailingPE, type: 'peer' })
  }
  const barColor = (t) => t === 'current' ? '#5c6bc0' : t === 'sector' ? '#6b7280' : '#4682b4'

  return (
    <>
      {/* Price header */}
      <div className="panel">
        <div className="chart-header">
          <span className="chart-name">{data.name}</span>
          <span className="chart-ticker-badge">{data.ticker}</span>
          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>{data.sector} · {data.industry}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div className="chart-price">{fmtPrice(data.currentPrice)}</div>
          {priceChange != null && (
            <div className={`chart-change ${isUp ? 'positive' : 'negative'}`}>
              {isUp ? '+' : ''}{priceChange.toFixed(2)} ({pctChange?.toFixed(2)}%)
            </div>
          )}
          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>Mkt Cap: {fmtCap(data.marketCap)}</span>
        </div>
        <div className="chart-meta">
          <span>Day High: <strong>{fmtPrice(data.dayHigh)}</strong></span>
          <span>Day Low: <strong>{fmtPrice(data.dayLow)}</strong></span>
          <span>Prev Close: <strong>{fmtPrice(data.previousClose)}</strong></span>
          <span>52W High: <strong>{fmtPrice(data.fiftyTwoWeekHigh)}</strong></span>
          <span>52W Low: <strong>{fmtPrice(data.fiftyTwoWeekLow)}</strong></span>
        </div>
      </div>

      {/* Valuation metrics */}
      <div className="panel">
        <div className="pe-section-title">Valuation</div>
        <div className="pe-valuation-grid">
          {[
            { label: 'TTM PE', value: fmt(data.trailingPE) },
            { label: 'Forward PE', value: fmt(data.forwardPE) },
            { label: '2yr Forward PE', value: fmt(data.twoYearForwardPE) },
            { label: 'Sector Avg PE', value: fmt(data.sectorPE) },
            { label: 'PEG Ratio', value: fmt(data.pegRatio) },
            { label: 'Price / Book', value: fmt(data.priceToBook) },
            { label: 'Price / Sales', value: fmt(data.priceToSales) },
            { label: 'EPS (TTM)', value: data.trailingEps != null ? `$${fmt(data.trailingEps, 2)}` : 'N/A' },
            { label: 'EPS (Forward)', value: data.forwardEps != null ? `$${fmt(data.forwardEps, 2)}` : 'N/A' },
          ].map(item => (
            <div key={item.label} className="pe-val-item">
              <div className="pe-val-label">{item.label}</div>
              <div className={`pe-val-value ${item.value === 'N/A' ? 'muted' : ''}`}>{item.value}</div>
            </div>
          ))}
        </div>

        <div className="pe-section-title" style={{ marginTop: '0.5rem' }}>Valuation vs Sector</div>
        <OvervaluationBar pct={data.overvaluationPct} />
      </div>

      {/* PE comparison chart */}
      <div className="panel">
        <div className="pe-section-title">TTM PE — Stock vs Sector vs Peers</div>
        {barData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData} layout="vertical" margin={{ top: 4, right: 50, left: 10, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#2a2d3a' }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} axisLine={false} width={76} />
              <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar dataKey="pe" radius={[0, 4, 4, 0]} barSize={16}>
                {barData.map((e, i) => <Cell key={i} fill={barColor(e.type)} />)}
                <LabelList dataKey="pe" position="right" formatter={v => v?.toFixed(1)} style={{ fill: '#9ca3af', fontSize: 10 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="loading-state" style={{ height: 80 }}>Loading peer data…</div>
        )}

        {peers.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <div className="pe-section-title">Peer Detail</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.5rem' }}>
              {peers.map(p => (
                <div key={p.ticker} className="pe-val-item">
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#e0e0e0', marginBottom: 2 }}>{p.ticker}</div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: 4 }}>{p.name}</div>
                  <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.78rem' }}>
                    <span style={{ color: '#9ca3af' }}>T.PE <strong style={{ color: '#e0e0e0' }}>{fmt(p.trailingPE)}</strong></span>
                    <span style={{ color: '#9ca3af' }}>F.PE <strong style={{ color: '#e0e0e0' }}>{fmt(p.forwardPE)}</strong></span>
                    <span style={{ color: '#9ca3af' }}>P/B <strong style={{ color: '#e0e0e0' }}>{fmt(p.priceToBook)}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}

export default StockDetail
