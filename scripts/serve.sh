#!/bin/bash
# Runs the JARVIS Console server. Used by the login item (LaunchAgent) and
# as a fallback by the launcher. Keeps JARVIS available at 127.0.0.1:8765.
cd "$(dirname "$0")/.." || exit 1
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="src"
unset ANTHROPIC_BASE_URL ANTHROPIC_API_BASE
exec .venv/bin/python -m uvicorn jarvis.web.server:app --host 127.0.0.1 --port 8765
