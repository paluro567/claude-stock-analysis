interface ScoreBarProps {
  label: string
  score: number
  color?: string
  fallback?: boolean
}

function barColor(color?: string, score?: number): string {
  if (color) return color
  const s = score ?? 50
  if (s >= 70) return 'var(--green)'
  if (s >= 40) return 'var(--yellow)'
  return 'var(--red)'
}

export function ScoreBar({ label, score, color, fallback }: ScoreBarProps) {
  const fill = barColor(color, score)
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-header">
        <span className="score-bar-label">
          {label}{fallback ? ' *' : ''}
        </span>
        <span className="score-bar-value" style={{ color: fill }}>
          {score.toFixed(1)}
        </span>
      </div>
      <div className="score-bar-track">
        <div
          className="score-bar-fill"
          style={{ width: `${Math.min(score, 100)}%`, background: fill }}
        />
      </div>
    </div>
  )
}
