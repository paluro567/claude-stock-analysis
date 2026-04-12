export function scoreColor(score: number): string {
  if (score >= 70) return 'var(--green)'
  if (score >= 40) return 'var(--yellow)'
  return 'var(--red)'
}

export function trimColor(score: number): string {
  if (score >= 60) return 'var(--red)'
  if (score >= 35) return 'var(--orange)'
  return 'var(--text-muted)'
}

export function addColor(score: number): string {
  if (score >= 60) return 'var(--green)'
  if (score >= 35) return 'var(--yellow)'
  return 'var(--text-muted)'
}

export function actionBadgeClass(action: string): string {
  const a = action.toLowerCase()
  if (a.includes('high conviction') || a === 'watchlist') return 'badge-green'
  if (a.includes('high priority') || a.includes('extended')) return 'badge-red'
  if (a.includes('partial') || a.includes('monitor')) return 'badge-orange'
  if (a === 'avoid') return 'badge-red'
  return 'badge-gray'
}

export function opportunityBadgeClass(opp: string): string {
  if (opp.includes('avoid')) return 'badge-red'
  if (opp.includes('uptrend') || opp.includes('breakout')) return 'badge-green'
  if (opp.includes('reversal') || opp.includes('bounce')) return 'badge-accent'
  return 'badge-gray'
}

export function flagBadgeClass(flag: string): string {
  if (flag === 'trim_candidate') return 'badge-red'
  if (flag === 'add_candidate') return 'badge-green'
  if (flag === 'high_catalyst_risk') return 'badge-orange'
  if (flag === 'concentration_risk') return 'badge-accent'
  return 'badge-gray'
}

export function flagLabel(flag: string): string {
  return flag.replace(/_/g, ' ')
}
