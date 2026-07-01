#!/usr/bin/env bash
# ==============================================================================
# JARVIS OS — Pre-Flight Check
# Verifies every system dependency, permission, model, and API key
# before you attempt to run JARVIS for the first time.
#
# Usage: bash scripts/preflight_check.sh
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

PASS=0
WARN=0
FAIL=0

pass()  { echo -e "  ${GREEN}✓${RESET} $*"; ((PASS++)); }
warn()  { echo -e "  ${YELLOW}⚠${RESET}  $*"; ((WARN++)); }
fail()  { echo -e "  ${RED}✗${RESET} $*"; ((FAIL++)); }
header(){ echo -e "\n${CYAN}${BOLD}$*${RESET}"; }

echo ""
echo -e "${CYAN}${BOLD}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║   JARVIS OS — Pre-Flight Check        ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${RESET}"

# ---------------------------------------------------------------------------
# 1. Operating System
# ---------------------------------------------------------------------------
header "1. Operating System"
if [[ "$OSTYPE" == "darwin"* ]]; then
    MACOS_VER=$(sw_vers -productVersion)
    MACOS_MAJOR=$(echo "$MACOS_VER" | cut -d. -f1)
    if [[ "$MACOS_MAJOR" -ge 12 ]]; then
        pass "macOS $MACOS_VER (Monterey or later) ✓"
    else
        warn "macOS $MACOS_VER detected. macOS 12 (Monterey)+ recommended."
    fi
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        pass "Apple Silicon (M-series) — native arm64"
    else
        pass "Intel x86_64"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    pass "Linux detected"
else
    warn "Unsupported OS: $OSTYPE. macOS and Linux are supported."
fi

# ---------------------------------------------------------------------------
# 2. Python
# ---------------------------------------------------------------------------
header "2. Python"
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -ge 11 ]]; then
        pass "Python $PY_VER ✓"
    else
        fail "Python $PY_VER found. JARVIS requires Python 3.11+."
        echo "    Install: brew install python@3.11"
    fi
else
    fail "Python 3 not found."
    echo "    Install: brew install python@3.11"
fi

# Virtual environment
if [[ -d ".venv" ]]; then
    if [[ -f ".venv/bin/python" ]]; then
        VENV_VER=$(.venv/bin/python --version 2>&1 | awk '{print $2}')
        pass "Virtual environment exists (.venv) — Python $VENV_VER"
    else
        warn ".venv exists but Python binary not found. Run: make setup"
    fi
else
    warn ".venv not found. Run: make setup  (or: bash scripts/setup.sh)"
fi

# pip
if command -v pip3 &>/dev/null; then
    PIP_VER=$(pip3 --version | awk '{print $2}')
    pass "pip $PIP_VER"
else
    warn "pip3 not found."
fi

# ---------------------------------------------------------------------------
# 3. Homebrew
# ---------------------------------------------------------------------------
header "3. Homebrew (macOS package manager)"
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &>/dev/null; then
        BREW_VER=$(brew --version | head -1 | awk '{print $2}')
        pass "Homebrew $BREW_VER ✓"
    else
        fail "Homebrew not found."
        echo "    Install: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi
fi

# ---------------------------------------------------------------------------
# 4. System Libraries
# ---------------------------------------------------------------------------
header "4. System Libraries"

check_brew() {
    local pkg="$1"
    local install_hint="$2"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if brew list "$pkg" &>/dev/null 2>&1 || command -v "$pkg" &>/dev/null; then
            pass "$pkg ✓"
            return 0
        fi
    fi
    if command -v "$pkg" &>/dev/null; then
        pass "$pkg ✓"
        return 0
    fi
    fail "$pkg not found. $install_hint"
    return 1
}

check_brew "git"      "Install: brew install git"
check_brew "ffmpeg"   "Install: brew install ffmpeg    [REQUIRED for voice pipeline]"

# PortAudio (needed by pyaudio)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if brew list portaudio &>/dev/null 2>&1; then
        pass "portaudio ✓  (required by pyaudio for microphone)"
    else
        fail "portaudio not found. Install: brew install portaudio"
    fi
else
    if ldconfig -p 2>/dev/null | grep -q "libportaudio"; then
        pass "portaudio ✓"
    else
        fail "portaudio not found. Install: sudo apt install portaudio19-dev"
    fi
fi

# ---------------------------------------------------------------------------
# 5. Python Package Dependencies
# ---------------------------------------------------------------------------
header "5. Python Packages (core)"

check_package() {
    local pkg="$1"
    local import_name="${2:-$1}"
    local critical="${3:-false}"

    if [[ -f ".venv/bin/python" ]]; then
        if .venv/bin/python -c "import $import_name" &>/dev/null 2>&1; then
            pass "$pkg ✓"
        elif [[ "$critical" == "true" ]]; then
            fail "$pkg NOT INSTALLED (critical). Run: make setup"
        else
            warn "$pkg not installed. Run: make setup"
        fi
    else
        warn "Cannot check packages — .venv not set up. Run: make setup"
        return
    fi
}

check_package "anthropic"           "anthropic"         "true"
check_package "pydantic"            "pydantic"          "true"
check_package "loguru"              "loguru"            "true"
check_package "aiosqlite"           "aiosqlite"         "true"
check_package "PySide6"       "PySide6"     "true"
check_package "atomacos"           "atomacos"
check_package "mss"         "mss"
check_package "playwright"          "playwright"
check_package "lancedb"            "lancedb"
check_package "faster-whisper"      "RealtimeSTT"
check_package "openwakeword"        "openwakeword"
check_package "pyaudio"             "pyaudio"
check_package "sounddevice"         "sounddevice"
check_package "TTS (Coqui)"         "TTS"
check_package "keyring"             "keyring"
check_package "cryptography"        "cryptography"
check_package "tenacity"            "tenacity"
check_package "typer"               "typer"
check_package "numpy"               "numpy"

# ---------------------------------------------------------------------------
# 6. Playwright Browsers
# ---------------------------------------------------------------------------
header "6. Playwright Browsers"

if [[ -f ".venv/bin/playwright" ]]; then
    CHROMIUM_PATH=$(.venv/bin/python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium.executable_path); p.stop()" 2>/dev/null || echo "")
    if [[ -n "$CHROMIUM_PATH" && -f "$CHROMIUM_PATH" ]]; then
        pass "Chromium browser installed ✓"
    else
        fail "Playwright browsers not installed."
        echo "    Install: .venv/bin/playwright install chromium firefox webkit"
    fi
else
    warn "Playwright not in .venv — run: make setup"
fi

# ---------------------------------------------------------------------------
# 7. AI Models (Downloaded on First Use)
# ---------------------------------------------------------------------------
header "7. AI Models"

# Whisper
WHISPER_CACHE="${HOME}/.cache/huggingface/hub"
WHISPER_MODELS_FOUND=0
if [[ -d "$WHISPER_CACHE" ]]; then
    WHISPER_MODELS_FOUND=$(find "$WHISPER_CACHE" -name "*.bin" 2>/dev/null | wc -l | tr -d ' ')
fi

if [[ "$WHISPER_MODELS_FOUND" -gt 0 ]]; then
    pass "Whisper STT models found in cache ($WHISPER_MODELS_FOUND .bin files)"
else
    warn "Whisper STT model not yet downloaded (~145MB for base.en)."
    echo "      It will auto-download on first JARVIS startup."
    echo "      Pre-download: python3 scripts/download_models.py --whisper"
fi

# Wake Word model
WAKEWORD_CACHE="${HOME}/.cache/openwakeword"
if [[ -d "$WAKEWORD_CACHE" ]] && ls "$WAKEWORD_CACHE"/*.tflite &>/dev/null 2>&1; then
    pass "Wake word models found in cache ✓"
else
    warn "Wake word models not yet downloaded (~20MB)."
    echo "      They will auto-download on first startup."
    echo "      Pre-download: python3 scripts/download_models.py --wakeword"
fi

# TTS
TTS_CACHE="${HOME}/Library/Application Support/tts"
if [[ "$OSTYPE" == "darwin"* && -d "$TTS_CACHE" ]] && ls "$TTS_CACHE"/*.pth &>/dev/null 2>&1; then
    pass "TTS voice models found ✓"
else
    warn "TTS voice model not yet downloaded (~100-200MB)."
    echo "      It will auto-download on first JARVIS startup."
    echo "      Pre-download: python3 scripts/download_models.py --tts"
    echo "      Alternative (no download): set JARVIS_VOICE_TTS_PROVIDER=pyttsx3 in .env"
fi

# ---------------------------------------------------------------------------
# 8. API Keys
# ---------------------------------------------------------------------------
header "8. API Keys"

if [[ -f ".env" ]]; then
    source_env() {
        set -a
        # shellcheck disable=SC1091
        source .env
        set +a
    }
    source_env 2>/dev/null || true

    PROVIDER="${JARVIS_AI_PROVIDER:-claude}"

    if [[ "$PROVIDER" == "claude" ]]; then
        if [[ -n "${ANTHROPIC_API_KEY:-}" && "${ANTHROPIC_API_KEY}" != "sk-ant-YOUR_KEY_HERE" ]]; then
            MASKED="${ANTHROPIC_API_KEY:0:8}...${ANTHROPIC_API_KEY: -4}"
            pass "ANTHROPIC_API_KEY set ($MASKED)"
        else
            fail "ANTHROPIC_API_KEY not set in .env (current provider: claude)"
            echo "    Get key: https://console.anthropic.com"
        fi
    elif [[ "$PROVIDER" == "openai" ]]; then
        if [[ -n "${OPENAI_API_KEY:-}" && "${OPENAI_API_KEY}" != "sk-YOUR_KEY_HERE" ]]; then
            MASKED="${OPENAI_API_KEY:0:5}...${OPENAI_API_KEY: -4}"
            pass "OPENAI_API_KEY set ($MASKED)"
        else
            fail "OPENAI_API_KEY not set in .env (current provider: openai)"
            echo "    Get key: https://platform.openai.com/api-keys"
        fi
    elif [[ "$PROVIDER" == "gemini" ]]; then
        if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
            pass "GOOGLE_API_KEY set"
        else
            fail "GOOGLE_API_KEY not set in .env"
        fi
    elif [[ "$PROVIDER" == "local" ]]; then
        MODEL_PATH="${JARVIS_AI_LOCAL_MODEL_PATH:-}"
        if [[ -n "$MODEL_PATH" && -f "$MODEL_PATH" ]]; then
            pass "Local model found: $MODEL_PATH"
        else
            fail "JARVIS_AI_LOCAL_MODEL_PATH not set or file not found in .env"
            echo "    Download a GGUF model from https://huggingface.co/TheBloke"
        fi
    fi
else
    fail ".env file not found. Copy: cp .env.example .env  then add your API key"
fi

# ---------------------------------------------------------------------------
# 9. macOS Permissions
# ---------------------------------------------------------------------------
header "9. macOS Permissions (must be granted manually)"

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "  The following permissions must be granted in:"
    echo "  System Settings → Privacy & Security"
    echo ""

    # Microphone — check via tccutil or just remind
    echo -e "  ${YELLOW}□${RESET}  Microphone      → Privacy & Security → Microphone"
    echo "     Required for: wake word detection, voice commands"
    echo ""
    echo -e "  ${YELLOW}□${RESET}  Accessibility   → Privacy & Security → Accessibility"
    echo "     Required for: keyboard control, mouse automation, hotkeys"
    echo ""
    echo -e "  ${YELLOW}□${RESET}  Screen Recording → Privacy & Security → Screen Recording"
    echo "     Required for: screenshot capture, OCR of screen content"
    echo ""
    echo -e "  ${YELLOW}□${RESET}  Full Disk Access → Privacy & Security → Full Disk Access"
    echo "     Required for: reading files across your entire filesystem"
    echo ""
    echo -e "  ${BLUE}ℹ${RESET}  JARVIS will prompt for each permission the first time"
    echo "     it tries to use that capability. You can also grant them"
    echo "     ahead of time by adding Terminal (or your IDE) to each list."

    ((WARN+=4))
else
    warn "Linux: ensure microphone access is granted to your terminal/user."
fi

# ---------------------------------------------------------------------------
# 10. Disk Space
# ---------------------------------------------------------------------------
header "10. Disk Space"

AVAIL_GB=$(df -g . 2>/dev/null | awk 'NR==2 {print $4}' || df -BG . 2>/dev/null | awk 'NR==2 {gsub("G",""); print $4}' || echo "?")
if [[ "$AVAIL_GB" != "?" ]]; then
    if [[ "$AVAIL_GB" -ge 10 ]]; then
        pass "${AVAIL_GB}GB available (need ~5GB for all models + packages)"
    elif [[ "$AVAIL_GB" -ge 5 ]]; then
        warn "${AVAIL_GB}GB available — tight but workable"
    else
        fail "Only ${AVAIL_GB}GB available. Need ~5GB minimum."
    fi
else
    warn "Could not determine available disk space."
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "${BOLD}Pre-Flight Summary${RESET}"
echo "═══════════════════════════════════════════════════════════"
echo -e "  ${GREEN}✓ Passed: $PASS${RESET}"
echo -e "  ${YELLOW}⚠ Warnings: $WARN${RESET}  (won't block startup)"
echo -e "  ${RED}✗ Failed: $FAIL${RESET}  (must fix before running)"
echo ""

if [[ "$FAIL" -eq 0 ]]; then
    echo -e "  ${GREEN}${BOLD}✅ System is READY to run JARVIS OS!${RESET}"
    echo ""
    echo "  Next step:"
    echo "    source .venv/bin/activate"
    echo "    make dev"
else
    echo -e "  ${RED}${BOLD}❌ Fix the $FAIL failing item(s) above first.${RESET}"
    echo ""
    echo "  Quick fix — run ALL system installs:"
    echo "    bash scripts/install_macos.sh"
    echo "    make setup"
fi
echo ""
