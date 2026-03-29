import { useState } from 'react'

function Sidebar({ positions, selected, onSelect, onAdd, onRemove }) {
  const [inputValue, setInputValue] = useState('')

  const handleAdd = () => {
    const val = inputValue.trim()
    if (val) {
      onAdd(val)
      setInputValue('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleAdd()
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">Portfolio</div>
      <div className="sidebar-list">
        {positions.map((ticker) => (
          <div
            key={ticker}
            className={`sidebar-item${selected === ticker ? ' selected' : ''}`}
            onClick={() => onSelect(ticker)}
          >
            <span className="sidebar-item-ticker">{ticker}</span>
            <button
              className="sidebar-remove-btn"
              onClick={(e) => {
                e.stopPropagation()
                onRemove(ticker)
              }}
              title={`Remove ${ticker}`}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11 3L3 11M3 3L11 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          </div>
        ))}
        {positions.length === 0 && (
          <div style={{ padding: '1rem', color: '#4b5563', fontSize: '0.8rem', textAlign: 'center' }}>
            No positions yet
          </div>
        )}
      </div>
      <div className="sidebar-add">
        <input
          type="text"
          placeholder="Add ticker…"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value.toUpperCase())}
          onKeyDown={handleKeyDown}
          maxLength={10}
        />
        <button onClick={handleAdd}>Add</button>
      </div>
    </aside>
  )
}

export default Sidebar
