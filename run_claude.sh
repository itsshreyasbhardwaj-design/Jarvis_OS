#!/bin/bash
# ─────────────────────────────────────────────────────────
# JARVIS OS — Claude Code Launcher (ALWAYS USE THIS)
# Routes through Headroom, sets opus-4-8, activates venv.
# Usage: bash run_claude.sh
# ─────────────────────────────────────────────────────────

# Headroom proxy — REQUIRED
export ANTHROPIC_BASE_URL=http://127.0.0.1:6767

# Model — ultracode (Opus 4.8)
export ANTHROPIC_MODEL=claude-opus-4-8

# Permanently bake into ~/.zshrc if not already there
grep -q "ANTHROPIC_BASE_URL" ~/.zshrc 2>/dev/null || echo 'export ANTHROPIC_BASE_URL=http://127.0.0.1:6767' >> ~/.zshrc
grep -q "ANTHROPIC_MODEL=claude-opus-4-8" ~/.zshrc 2>/dev/null || echo 'export ANTHROPIC_MODEL=claude-opus-4-8' >> ~/.zshrc

# Ensure we're in the jarvis-os root
cd "$(dirname "$0")"

# Activate venv if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo ""
echo "✓ ANTHROPIC_BASE_URL = $ANTHROPIC_BASE_URL"
echo "✓ ANTHROPIC_MODEL    = $ANTHROPIC_MODEL"
echo "✓ Directory: $(pwd)"
echo "✓ Launching Claude Code..."
echo ""

exec claude "$@"
