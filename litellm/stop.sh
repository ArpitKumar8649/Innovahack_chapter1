#!/usr/bin/env bash
# Stop the LiteLLM proxy.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f proxy.pid ]] && kill -0 "$(cat proxy.pid)" 2>/dev/null; then
  kill "$(cat proxy.pid)"
  echo "Stopped proxy (pid $(cat proxy.pid))."
else
  echo "Proxy is not running."
fi
rm -f proxy.pid
