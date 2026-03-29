import { useState, useEffect } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts'
import axios from 'axios'

function fmt(v, decimals = 1) {
  if (v == null) return 'N/A'
  return Number(v).toFixed(decimals)
}

function fmtLarge(v) {
  if (v == null) return 'N/A'
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  return `$${v}`
}

const CustomBarTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: '#232635',
        border: '1px solid #2a2d3a',
        borderRadius: 6,
        padding: '6px 10px',
        fontSize: '0.78rem',
        color: '#e0e0e0',
      }}>
        <div style={{ color: '#9ca3af', marginBottom: 2 }}>{label}</div>
        <div>PE: <strong>{payload[0]?.value?.toFixed(1) ?? 'N/A'}</strong></div>
      </div>
    )
  }
  return null
}

function PEPanel({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    setData(null)
    axios.get(`/api/stock/${ticker}`)
      .then(res => {
        setData(res.data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.response?.data?.detail || err.message || 'Failed to load data')
        setLoading(false)
      })
  }, [ticker])

  if (loading) {
    return (
      <div className="panel">
        <div className="loading-state">Loading PE data…</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="panel">
        <div className="error-state">Error: {error}</div>
      </div>
    )
  }

  // Build bar chart data
  const barData = []

  if (data.trailingPE != null) {
    barData.push({ name: ticker, pe: data.trailingPE, type: 'current' })
  }

  if (data.sectorPE != null) {
    barData.push({ name: 'Sector Avg', pe: data.sectorPE, type: 'sector' })
  }

  if (data.peers) {
    for (const peer of data.peers) {
      if (peer.trailingPE != null) {
        barData.push({ name: peer.ticker, pe: peer.trailingPE, type: 'peer' })
      }
    }
  }

  const getBarColor = (type) => {
    if (type === 'current') return '#5c6bc0'
    if (type === 'sector') return '#6b7280'
    return '#4682b4'
  }

  return (
    <div className="panel">
      {/* Section 1: Current Valuation */}
      <div className="pe-section-title">Current Valuation</div>
      <div className="pe-valuation-grid">
        <div className="pe-val-item">
          <div className="pe-val-label">Trailing PE</div>
          <div className={`pe-val-value${data.trailingPE == null ? ' muted' : ''}`}>
            {fmt(data.trailingPE)}
          </div>
        </div>
        <div className="pe-val-item">
          <div className="pe-val-label">Forward PE</div>
          <div className={`pe-val-value${data.forwardPE == null ? ' muted' : ''}`}>
            {fmt(data.forwardPE)}
          </div>
        </div>
        <div className="pe-val-item">
          <div className="pe-val-label">Sector</div>
          <div className={`pe-val-value${!data.sector ? ' muted' : ''}`} style={{ fontSize: '0.85rem' }}>
            {data.sector || 'N/A'}
          </div>
        </div>
        <div className="pe-val-item">
          <div className="pe-val-label">Industry</div>
          <div className={`pe-val-value${!data.industry ? ' muted' : ''}`} style={{ fontSize: '0.8rem' }}>
            {data.industry || 'N/A'}
          </div>
        </div>
        <div className="pe-val-item">
          <div className="pe-val-label">Market Cap</div>
          <div className={`pe-val-value${data.marketCap == null ? ' muted' : ''}`}>
            {fmtLarge(data.marketCap)}
          </div>
        </div>
        <div className="pe-val-item">
          <div className="pe-val-label">Sector Avg PE</div>
          <div className={`pe-val-value${data.sectorPE == null ? ' muted' : ''}`}>
            {data.sectorPE ?? 'N/A'}
          </div>
        </div>
      </div>

      {/* Section 2: PE Comparison chart */}
      <div className="pe-section-title">PE Comparison</div>
      {barData.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={barData}
            layout="vertical"
            margin={{ top: 4, right: 50, left: 10, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#2a2d3a' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={72}
            />
            <Tooltip content={<CustomBarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Bar dataKey="pe" radius={[0, 4, 4, 0]} barSize={18}>
              {barData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.type)} />
              ))}
              <LabelList
                dataKey="pe"
                position="right"
                formatter={(v) => v?.toFixed(1)}
                style={{ fill: '#9ca3af', fontSize: 10 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="loading-state" style={{ height: 120 }}>
          No PE comparison data available
        </div>
      )}

      {/* Peer detail table */}
      {data.peers && data.peers.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <div className="pe-section-title">Peers</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.5rem' }}>
            {data.peers.map(peer => (
              <div key={peer.ticker} className="pe-val-item">
                <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#e0e0e0', marginBottom: 2 }}>{peer.ticker}</div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: 4 }}>{peer.name}</div>
                <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.78rem' }}>
                  <span style={{ color: '#9ca3af' }}>T.PE: <strong style={{ color: '#e0e0e0' }}>{fmt(peer.trailingPE)}</strong></span>
                  <span style={{ color: '#9ca3af' }}>F.PE: <strong style={{ color: '#e0e0e0' }}>{fmt(peer.forwardPE)}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default PEPanel
