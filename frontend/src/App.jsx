import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import StockChart from './components/StockChart'
import PEPanel from './components/PEPanel'
import ComparePage from './components/ComparePage'
import './App.css'

const DEFAULT_POSITIONS = ['AAPL', 'MSFT', 'NVDA', 'JPM']
const STORAGE_KEY = 'portfolio_positions'

function App() {
  const [page, setPage] = useState('portfolio')

  const [positions, setPositions] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed
      }
    } catch (e) {}
    return DEFAULT_POSITIONS
  })

  const [selectedTicker, setSelectedTicker] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed[0]
      }
    } catch (e) {}
    return DEFAULT_POSITIONS[0]
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(positions))
  }, [positions])

  const handleAdd = (ticker) => {
    const upper = ticker.toUpperCase().trim()
    if (upper && !positions.includes(upper)) {
      setPositions(prev => [...prev, upper])
      setSelectedTicker(upper)
    }
  }

  const handleRemove = (ticker) => {
    setPositions(prev => {
      const next = prev.filter(t => t !== ticker)
      if (selectedTicker === ticker && next.length > 0) {
        setSelectedTicker(next[0])
      } else if (next.length === 0) {
        setSelectedTicker(null)
      }
      return next
    })
  }

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <div className="top-nav-brand">Stock Analytics</div>
        <div className="top-nav-tabs">
          <button
            className={`top-nav-tab ${page === 'portfolio' ? 'active' : ''}`}
            onClick={() => setPage('portfolio')}
          >
            Portfolio
          </button>
          <button
            className={`top-nav-tab ${page === 'compare' ? 'active' : ''}`}
            onClick={() => setPage('compare')}
          >
            Compare
          </button>
        </div>
      </nav>

      <div className="app-container">
        {page === 'portfolio' && (
          <>
            <Sidebar
              positions={positions}
              selected={selectedTicker}
              onSelect={setSelectedTicker}
              onAdd={handleAdd}
              onRemove={handleRemove}
            />
            <main className="main-content">
              {selectedTicker ? (
                <>
                  <StockChart ticker={selectedTicker} />
                  <PEPanel ticker={selectedTicker} />
                </>
              ) : (
                <div className="empty-state">
                  <p>Add a stock to your portfolio to get started.</p>
                </div>
              )}
            </main>
          </>
        )}

        {page === 'compare' && (
          <main className="main-content">
            <ComparePage />
          </main>
        )}
      </div>
    </div>
  )
}

export default App
