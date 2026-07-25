#!/usr/bin/env bash
# Run VeriFact locally.
set -euo pipefail
cd "$(dirname "$0")/verifact/backend"

if ! python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null; then
  echo "Installing dependencies…"
  pip install -r requirements.txt
fi

echo "VeriFact → http://localhost:8000"
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
