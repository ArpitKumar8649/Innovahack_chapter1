#!/usr/bin/env bash
# Start the LiteLLM key-rotation proxy (idempotent — restarts if already up).
#
#   ./start.sh          # start (or restart) the proxy on port 4000
#
# First run: seeds .env from .env.example and copies your current
# ANTHROPIC_AUTH_TOKEN in as GATEWAY_API_KEY_1, so it works immediately.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-4000}"

# --- one-time bootstrap -----------------------------------------------------
if [[ ! -f .env ]]; then
  cp .env.example .env
  if [[ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    # seed KEY_1 with the gateway token Claude Code is already using
    sed -i "s|^GATEWAY_API_KEY_1=.*|GATEWAY_API_KEY_1=${ANTHROPIC_AUTH_TOKEN}|" .env
    echo "Seeded GATEWAY_API_KEY_1 from your current ANTHROPIC_AUTH_TOKEN."
  fi
  if ! grep -q '^LITELLM_MASTER_KEY=.\+' .env; then
    KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    sed -i "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=${KEY}|" .env
    echo "Generated LITELLM_MASTER_KEY."
  fi
fi

# --- venv -------------------------------------------------------------------
if [[ ! -x .venv/bin/litellm ]]; then
  echo "Installing litellm[proxy] into .venv (one-time)…"
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet 'litellm[proxy]'
fi

# --- generate config.yaml from .env ------------------------------------------
.venv/bin/python gen_config.py

# --- restart if already running ----------------------------------------------
if [[ -f proxy.pid ]] && kill -0 "$(cat proxy.pid)" 2>/dev/null; then
  echo "Stopping existing proxy (pid $(cat proxy.pid))…"
  kill "$(cat proxy.pid)" 2>/dev/null || true
  for _ in $(seq 1 20); do
    kill -0 "$(cat proxy.pid)" 2>/dev/null || break
    sleep 0.5
  done
fi

# --- launch ------------------------------------------------------------------
set -a; source .env; set +a
nohup .venv/bin/litellm --config config.yaml --port "$PORT" \
  > proxy.log 2>&1 &
echo $! > proxy.pid
echo "LiteLLM proxy starting on port $PORT (pid $(cat proxy.pid), log: proxy.log)"

# --- wait for health ---------------------------------------------------------
for i in $(seq 1 60); do
  if curl -fsS "http://localhost:${PORT}/health/liveliness" >/dev/null 2>&1; then
    echo "✅ Proxy is up: http://localhost:${PORT}"
    echo
    echo "Point Claude Code at it with:"
    echo "  export ANTHROPIC_BASE_URL=http://localhost:${PORT}"
    echo "  export ANTHROPIC_AUTH_TOKEN=${LITELLM_MASTER_KEY}"
    echo "  export ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-main   # all tiers → the one live model"
    echo
    echo "Or:  source use-litellm.env"
    exit 0
  fi
  sleep 1
done

echo "❌ Proxy did not become healthy in 60s — check proxy.log:" >&2
tail -n 30 proxy.log >&2
exit 1
