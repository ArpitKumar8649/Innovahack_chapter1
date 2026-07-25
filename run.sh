#!/usr/bin/env bash
# Run VeritasAI locally: API on :8000, React frontend on :3000 (proxies /api/*).
# Mirrors the production layout (nginx edge + API) from deploy/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/verifact/backend"

# load local env (LLM routing etc.) if present
[ -f .env ] && set -a && . ./.env && set +a

if ! python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null; then
  echo "Installing Python dependencies…"
  pip install -r requirements.txt
fi

# build the React frontend if it hasn't been built yet (or FORCE_BUILD=1)
if [ "${FORCE_BUILD:-0}" = "1" ] || [ ! -f "$ROOT/web/dist/index.html" ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "Building React frontend…"
    (cd "$ROOT/web" && [ -d node_modules ] || npm install --silent) && \
      (cd "$ROOT/web" && npm run build)
  else
    echo "⚠ npm not found — frontend will fall back to the legacy build if present."
  fi
fi

python3 ../frontend/serve_frontend.py &
FRONTEND_PID=$!
trap 'kill $FRONTEND_PID 2>/dev/null' EXIT

echo "VeritasAI API      → http://localhost:${PORT:-8000}"
echo "VeritasAI frontend → http://localhost:3000   ← open this"
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
