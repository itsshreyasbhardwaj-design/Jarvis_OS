#!/bin/bash
# ============================================================
#   Talk to JARVIS — double-click this file to start chatting.
# ============================================================
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="src"

# Don't route Claude through a local proxy that isn't running (Headroom).
unset ANTHROPIC_BASE_URL ANTHROPIC_API_BASE

clear
echo "Starting JARVIS…"
echo
exec .venv/bin/python -m jarvis.cli chat
