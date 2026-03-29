#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Starting backend on port 8002..."
cd "$SCRIPT_DIR/backend"
uvicorn main:app --reload --port 8002 &
BACKEND_PID=$!
echo "    Backend PID: $BACKEND_PID"

echo "==> Checking frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  echo "    node_modules not found — running npm install..."
  npm install
fi

echo "==> Starting frontend dev server..."
npm run dev

# If frontend exits, kill backend
kill $BACKEND_PID 2>/dev/null || true
