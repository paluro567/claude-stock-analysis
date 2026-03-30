// Simple in-memory cache for stock data — 5 minute TTL
const _cache = {}
const TTL_MS = 5 * 60 * 1000

export function cacheGet(key) {
  const entry = _cache[key]
  if (entry && Date.now() - entry.ts < TTL_MS) {
    return entry.data
  }
  return null
}

export function cacheSet(key, data) {
  _cache[key] = { data, ts: Date.now() }
}
