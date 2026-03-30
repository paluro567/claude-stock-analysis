import { useState, useEffect } from 'react'
import {
  ComposedChart,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Label,
} from 'recharts'
import axios from 'axios'
import { cacheGet, cacheSet } from '../utils/stockCache'

function formatPrice(v) {
  if (v == null) return 'N/A'
  return `$${Number(v).toFixed(2)}`
}

function formatMarketCap(v) {
  if (v == null) return 'N/A'
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
  return `$${v}`
}

const CustomTooltip = ({ active, payload, label }) => {
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
        <div>Close: <strong>{formatPrice(payload[0]?.value)}</strong></div>
      </div>
    )
  }
  return null
}

function StockChart({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const cached = cacheGet(ticker)
    if (cached) {
      setData(cached)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    setData(null)
    axios.get(`/api/stock/${ticker}`)
      .then(res => {
        cacheSet(ticker, res.data)
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
        <div className="loading-state">Loading {ticker}…</div>
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

  const priceChange = data.currentPrice != null && data.previousClose != null
    ? data.currentPrice - data.previousClose
    : null
  const pctChange = priceChange != null && data.previousClose
    ? (priceChange / data.previousClose) * 100
    : null
  const isPositive = priceChange != null ? priceChange >= 0 : null

  const chartData = (data.intraday || []).filter(d => d.close != null)

  // Compute Y domain with padding
  const closes = chartData.map(d => d.close)
  const levels = [data.pivot, data.r1, data.r2, data.s1, data.s2].filter(v => v != null)
  const allValues = [...closes, ...levels].filter(v => v != null)
  let yMin = Math.min(...allValues)
  let yMax = Math.max(...allValues)
  const yPad = (yMax - yMin) * 0.05 || 1
  yMin = yMin - yPad
  yMax = yMax + yPad

  return (
    <div className="panel">
      <div className="chart-header">
        <span className="chart-name">{data.name}</span>
        <span className="chart-ticker-badge">{data.ticker}</span>
        {data.marketCap && (
          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
            Mkt Cap: {formatMarketCap(data.marketCap)}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div className="chart-price">{formatPrice(data.currentPrice)}</div>
        {priceChange != null && (
          <div className={`chart-change ${isPositive ? 'positive' : 'negative'}`}>
            {isPositive ? '+' : ''}{priceChange.toFixed(2)} ({pctChange?.toFixed(2)}%)
          </div>
        )}
      </div>
      <div className="chart-meta">
        <span>High: <strong>{formatPrice(data.dayHigh)}</strong></span>
        <span>Low: <strong>{formatPrice(data.dayLow)}</strong></span>
        <span>Prev Close: <strong>{formatPrice(data.previousClose)}</strong></span>
      </div>

      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={chartData} margin={{ top: 8, right: 80, left: 10, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
            <XAxis
              dataKey="time"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#2a2d3a' }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[yMin, yMax]}
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#2a2d3a' }}
              tickFormatter={(v) => `$${v.toFixed(0)}`}
              width={58}
            />
            <Tooltip content={<CustomTooltip />} />

            <Line
              type="monotone"
              dataKey="close"
              stroke="#5c6bc0"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#5c6bc0' }}
            />

            {data.s2 != null && (
              <ReferenceLine y={data.s2} stroke="#ef4444" strokeDasharray="4 3" strokeWidth={1.5}>
                <Label value={`S2 ${data.s2.toFixed(2)}`} position="right" fill="#ef4444" fontSize={10} />
              </ReferenceLine>
            )}
            {data.s1 != null && (
              <ReferenceLine y={data.s1} stroke="#f97316" strokeDasharray="4 3" strokeWidth={1.5}>
                <Label value={`S1 ${data.s1.toFixed(2)}`} position="right" fill="#f97316" fontSize={10} />
              </ReferenceLine>
            )}
            {data.pivot != null && (
              <ReferenceLine y={data.pivot} stroke="#9ca3af" strokeWidth={1.5}>
                <Label value={`P  ${data.pivot.toFixed(2)}`} position="right" fill="#9ca3af" fontSize={10} />
              </ReferenceLine>
            )}
            {data.r1 != null && (
              <ReferenceLine y={data.r1} stroke="#86efac" strokeDasharray="4 3" strokeWidth={1.5}>
                <Label value={`R1 ${data.r1.toFixed(2)}`} position="right" fill="#86efac" fontSize={10} />
              </ReferenceLine>
            )}
            {data.r2 != null && (
              <ReferenceLine y={data.r2} stroke="#4ade80" strokeDasharray="4 3" strokeWidth={1.5}>
                <Label value={`R2 ${data.r2.toFixed(2)}`} position="right" fill="#4ade80" fontSize={10} />
              </ReferenceLine>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      ) : (
        <div className="loading-state" style={{ height: 200 }}>
          No intraday data available
        </div>
      )}
    </div>
  )
}

export default StockChart
