#!/usr/bin/env bash
# ==============================================================================
# JARVIS OS — macOS System Dependencies Installer
# Installs everything that cannot be done via pip.
# Run this ONCE before running scripts/setup.sh.
#
# Usage: bash scripts/install_macos.sh
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   JARVIS OS — macOS Dependency Installer ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${RESET}"

# macOS only
if [[ "$OSTYPE" != "darwin"* ]]; then
    error "This script is for macOS only. See docs/development/setup.md for Linux."
fi

# ---------------------------------------------------------------------------
# 1. Xcode Command Line Tools (required by Homebrew and git)
# ---------------------------------------------------------------------------
info "Checking Xcode Command Line Tools..."
if xcode-select -p &>/dev/null; then
    success "Xcode CLT already installed ✓"
else
    info "Installing Xcode Command Line Tools (this may take a few minutes)..."
    xcode-select --install
    info "Wait for the installer to complete, then re-run this script."
    exit 0
fi

# ---------------------------------------------------------------------------
# 2. Homebrew
# ---------------------------------------------------------------------------
info "Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add to PATH for Apple Silicon
    if [[ "$(uname -m)" == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "${HOME}/.zprofile"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    success "Homebrew installed ✓"
else
    info "Homebrew found. Updating..."
    brew update --quiet
    success "Homebrew up to date ✓"
fi

# ---------------------------------------------------------------------------
# 3. Python 3.11+
# ---------------------------------------------------------------------------
info "Checking Python 3.11+..."
if python3 -c 'import sys; assert sys.version_info >= (3,11)' &>/dev/null; then
    PY_VER=$(python3 --version | awk '{print $2}')
    success "Python $PY_VER already installed ✓"
else
    info "Installing Python 3.11..."
    brew install python@3.11
    brew link python@3.11 --force --overwrite
    success "Python 3.11 installed ✓"
fi

# ---------------------------------------------------------------------------
# 4. Core System Libraries
# ---------------------------------------------------------------------------
info "Installing core system libraries..."

PACKAGES=(
    "git"                   # Version control
    "ffmpeg"                # Audio/video processing (REQUIRED for voice pipeline)
    "portaudio"             # Audio I/O for sounddevice microphone capture
    "libomp"                # OpenMP for numpy / lancedb performance
    "cmake"                 # Build tool needed by some Python packages
    "pkg-config"            # Library config for compiled packages
    "llama.cpp"             # C++ inference backend used by RealtimeSTT whisper.cpp
    # NOTE: tesseract removed — Apple Vision (pyobjc-framework-Vision) used instead
    # It's built into macOS; zero installation required
)

for pkg in "${PACKAGES[@]}"; do
    name="${pkg%%#*}"       # strip comment
    name="${name%% *}"      # strip trailing spaces
    if brew list "$name" &>/dev/null 2>&1; then
        success "$name already installed ✓"
    else
        info "Installing $name..."
        brew install "$name"
        success "$name installed ✓"
    fi
done

# ---------------------------------------------------------------------------
# 5. Optional: Rosetta 2 (Apple Silicon only, needed for some x86 packages)
# ---------------------------------------------------------------------------
if [[ "$(uname -m)" == "arm64" ]]; then
    info "Apple Silicon detected — checking Rosetta 2..."
    if /usr/bin/pgrep oahd &>/dev/null; then
        success "Rosetta 2 already installed ✓"
    else
        info "Installing Rosetta 2 (needed for some x86_64 packages)..."
        softwareupdate --install-rosetta --agree-to-license
        success "Rosetta 2 installed ✓"
    fi
fi

# ---------------------------------------------------------------------------
# 6. Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║  macOS System Dependencies Installed ✓   ║${RESET}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo "  Next steps:"
echo "  1. bash scripts/setup.sh       ← Install Python packages + configure"
echo "  2. python3 scripts/download_models.py  ← Pre-download AI models"
echo "  3. bash scripts/preflight_check.sh    ← Verify everything is ready"
echo "  4. make dev                    ← Start JARVIS"
echo ""

# ---------------------------------------------------------------------------
# 7. Headroom proxy fix — Claude Code must route through Headroom
# ---------------------------------------------------------------------------
ZSHRC="$HOME/.zshrc"
BASHRC="$HOME/.bashrc"
HEADROOM_LINE='export ANTHROPIC_BASE_URL=http://127.0.0.1:6767'

for RC_FILE in "$ZSHRC" "$BASHRC"; do
    if [ -f "$RC_FILE" ] && ! grep -q "ANTHROPIC_BASE_URL" "$RC_FILE"; then
        echo "" >> "$RC_FILE"
        echo "# Headroom proxy for Claude Code" >> "$RC_FILE"
        echo "$HEADROOM_LINE" >> "$RC_FILE"
        echo "  ✓ Added Headroom proxy to $RC_FILE"
    fi
done

# Apply immediately to current shell session
export ANTHROPIC_BASE_URL=http://127.0.0.1:6767
echo "  ✓ ANTHROPIC_BASE_URL set for this session"
