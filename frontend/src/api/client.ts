import type {
  PortfolioSummaryResponse,
  Position,
  TrimCandidatesResponse,
  AddCandidatesResponse,
  ReviewQueueResponse,
} from '../types'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status} ${path}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getPortfolioSummary: () =>
    get<PortfolioSummaryResponse>('/portfolio/summary'),

  getPositions: () =>
    get<Position[]>('/positions'),

  getPosition: (ticker: string) =>
    get<Position>(`/positions/${ticker.toUpperCase()}`),

  getTrimCandidates: () =>
    get<TrimCandidatesResponse>('/trim-candidates'),

  getAddCandidates: () =>
    get<AddCandidatesResponse>('/add-candidates'),

  getReviewQueue: () =>
    get<ReviewQueueResponse>('/review-queue'),
}
