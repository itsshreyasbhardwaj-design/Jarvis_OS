#!/bin/bash
# ============================================================
#   JARVIS Console — opens the interface in your browser.
#   The server runs in the background (login item). This just
#   opens it, and starts the server too if it isn't running.
# ============================================================
cd "$(dirname "$0")" || exit 1
URL="http://127.0.0.1:8765"

if ! curl -s -o /dev/null "$URL/api/status"; then
  echo "Starting JARVIS server…"
  export PATH="$HOME/.local/bin:$PATH"
  export PYTHONPATH="src"
  unset ANTHROPIC_BASE_URL ANTHROPIC_API_BASE
  (.venv/bin/python -m uvicorn jarvis.web.server:app --host 127.0.0.1 --port 8765 \
     >/tmp/jarvis-console.log 2>&1 &)
  for _ in $(seq 1 60); do curl -s -o /dev/null "$URL/api/status" && break; done
fi

open "$URL"
echo "JARVIS is open in your browser."
