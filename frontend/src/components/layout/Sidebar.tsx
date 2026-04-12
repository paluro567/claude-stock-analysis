import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/',               label: 'Overview' },
  { to: '/positions',      label: 'Positions' },
  { to: '/trim-watchlist', label: 'Trim Watchlist' },
  { to: '/add-candidates', label: 'Add Candidates' },
  { to: '/review-queue',   label: 'Review Queue' },
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">PortfolioOS</div>
      <nav className="sidebar-nav">
        {NAV.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
