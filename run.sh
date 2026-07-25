#!/usr/bin/env bash
# Run VeritasAI locally: API on :8000, frontend on :3000 (proxies /api/*).
# Mirrors the production layout (nginx edge + API) from deploy/.
set -euo pipefail
cd "$(dirname "$0")/verifact/backend"

if ! python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null; then
  echo "Installing dependencies…"
  pip install -r requirements.txt
fi

python3 ../frontend/serve_frontend.py &
FRONTEND_PID=$!
trap 'kill $FRONTEND_PID 2>/dev/null' EXIT

echo "VeritasAI API      → http://localhost:${PORT:-8000}"
echo "VeritasAI frontend → http://localhost:3000   ← open this"
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
