#!/usr/bin/env bash
# ==============================================================================
# JARVIS OS — Automated Development Environment Setup
# Run this once after cloning the repository.
# Usage: bash scripts/setup.sh
# ==============================================================================

set -euo pipefail

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }
step()    { echo -e "\n${CYAN}>>> $*${RESET}"; }

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════╗"
echo "  ║       JARVIS OS — Setup          ║"
echo "  ║   Production Foundation v0.1.0   ║"
echo "  ╚══════════════════════════════════╝"
echo -e "${RESET}"

# ---------------------------------------------------------------------------
# 1. Python Version Check
# ---------------------------------------------------------------------------
step "Checking Python version..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Install Python 3.11+ from https://python.org"
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_MAJOR=3
REQUIRED_MINOR=11

python3 -c "
import sys
if sys.version_info < (3, 11):
    print(f'Python 3.11+ required, found {sys.version}')
    sys.exit(1)
" || error "Python 3.11+ required. Current: $PYTHON_VERSION. Download: https://python.org/downloads"

success "Python $PYTHON_VERSION ✓"

# ---------------------------------------------------------------------------
# 2. System Dependencies
# ---------------------------------------------------------------------------
step "Checking system dependencies..."

check_command() {
    local cmd=$1
    local install_msg=$2
    if command -v "$cmd" &>/dev/null; then
        success "$cmd found ✓"
    else
        warn "$cmd not found. $install_msg"
    fi
}

check_command git       "Install git: https://git-scm.com"
check_command ffmpeg    "Install ffmpeg (for voice): brew install ffmpeg / apt install ffmpeg"
check_command tesseract "Install Tesseract (for OCR): brew install tesseract / apt install tesseract-ocr"

# macOS specific
if [[ "$OSTYPE" == "darwin"* ]]; then
    check_command brew "Install Homebrew: https://brew.sh"
    info "macOS detected. Consider: brew install portaudio ffmpeg tesseract"
fi

# Linux specific
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    info "Linux detected. Consider: sudo apt install portaudio19-dev python3-pyaudio ffmpeg tesseract-ocr libnotify-dev"
fi

# ---------------------------------------------------------------------------
# 3. Virtual Environment
# ---------------------------------------------------------------------------
step "Setting up Python virtual environment..."

if [[ -d ".venv" ]]; then
    warn ".venv already exists. Skipping creation."
else
    python3 -m venv .venv
    success "Virtual environment created at .venv/ ✓"
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate
success "Virtual environment activated ✓"

# ---------------------------------------------------------------------------
# 4. Pip Upgrade
# ---------------------------------------------------------------------------
step "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel --quiet
success "pip $(pip --version | awk '{print $2}') ✓"

# ---------------------------------------------------------------------------
# 5. Install Dependencies
# ---------------------------------------------------------------------------
step "Installing JARVIS OS + dev dependencies..."
pip install -e ".[dev]" --quiet
success "All dependencies installed ✓"

# ---------------------------------------------------------------------------
# 6. Playwright Browsers
# ---------------------------------------------------------------------------
step "Installing Playwright browsers (Chromium, Firefox)..."
playwright install chromium firefox webkit
success "Playwright browsers installed ✓"

# ---------------------------------------------------------------------------
# 7. Pre-commit Hooks
# ---------------------------------------------------------------------------
step "Installing pre-commit hooks..."
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
success "Pre-commit hooks installed ✓"

# ---------------------------------------------------------------------------
# 8. Environment File
# ---------------------------------------------------------------------------
step "Setting up environment configuration..."
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    success ".env created from .env.example ✓"
    warn "⚠️  Edit .env and add your API keys before running JARVIS!"
else
    info ".env already exists, skipping."
fi

# ---------------------------------------------------------------------------
# 9. Data Directories
# ---------------------------------------------------------------------------
step "Creating data directories..."
mkdir -p data/{logs,memory/{short_term,long_term,vector_store},models,audit,plugins}
success "Data directories ready ✓"

# ---------------------------------------------------------------------------
# 10. Git Configuration
# ---------------------------------------------------------------------------
step "Checking git repository..."
if [[ ! -d ".git" ]]; then
    git init
    git add .
    git commit -m "chore: initial JARVIS OS foundation setup"
    success "Git repository initialized ✓"
else
    success "Git repository exists ✓"
fi

# ---------------------------------------------------------------------------
# Done!
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║   JARVIS OS Foundation Ready! ✓       ║${RESET}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${RESET}"
echo ""
echo "  Next steps:"
echo "  1. Edit .env and add your API keys"
echo "  2. Run: source .venv/bin/activate"
echo "  3. Run: make dev        (start in development mode)"
echo "  4. Run: make test       (run the test suite)"
echo "  5. Read: docs/development/setup.md"
echo ""

# ── Headroom proxy fix ──────────────────────────────────────
HEADROOM_LINE='export ANTHROPIC_BASE_URL=http://127.0.0.1:6767'
for RC in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
    [ -f "$RC" ] || continue
    grep -q "ANTHROPIC_BASE_URL" "$RC" && continue
    echo "" >> "$RC"
    echo "# Headroom Claude proxy (required for Claude Code + Headroom)" >> "$RC"
    echo "$HEADROOM_LINE" >> "$RC"
    echo "  ✓ Headroom proxy written to $RC"
done
export ANTHROPIC_BASE_URL=http://127.0.0.1:6767
echo "  ✓ ANTHROPIC_BASE_URL active for this session"
