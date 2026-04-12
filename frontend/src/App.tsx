import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { Overview } from './pages/Overview'
import { Positions } from './pages/Positions'
import { TrimWatchlist } from './pages/TrimWatchlist'
import { AddCandidates } from './pages/AddCandidates'
import { ReviewQueue } from './pages/ReviewQueue'
import { PositionDetail } from './pages/PositionDetail'

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <Sidebar />
        <div className="main-area">
          <Routes>
            <Route path="/"               element={<Overview />} />
            <Route path="/positions"      element={<Positions />} />
            <Route path="/positions/:ticker" element={<PositionDetail />} />
            <Route path="/trim-watchlist" element={<TrimWatchlist />} />
            <Route path="/add-candidates" element={<AddCandidates />} />
            <Route path="/review-queue"   element={<ReviewQueue />} />
            <Route path="*"              element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
