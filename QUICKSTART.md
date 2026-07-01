# JARVIS OS — Quick Start Guide

This is the **complete, zero-to-voice-commands** guide. Follow every step in order.

---

## What You're Installing

| Component | Size | Purpose |
|-----------|------|---------|
| Python packages | ~500 MB | Core runtime |
| Playwright browsers | ~300 MB | Web automation |
| Whisper STT model | ~145 MB | Voice → text |
| Wake word model | ~20 MB | "Hey JARVIS" detection |
| TTS voice model | ~120 MB | Text → JARVIS voice |
| **Total** | **~1.1 GB** | |

Everything downloads automatically. You need ~5 GB free disk space.

---

## Step 1 — Install macOS System Dependencies

These are C libraries that Python packages build on. Must be installed before pip.

```bash
bash scripts/install_macos.sh
```

This installs (via Homebrew):
- `ffmpeg` — audio processing for the voice pipeline
- `tesseract` — OCR so JARVIS can read your screen
- `portaudio` — microphone/speaker access for pyaudio
- `cmake`, `pkg-config` — build tools for compiled Python packages
- Python 3.11 (if not already installed)

**Time: ~5-10 minutes**

---

## Step 2 — Set Up Python Environment

```bash
bash scripts/setup.sh
```

This:
1. Creates `.venv/` virtual environment
2. Installs all 48 Python packages from `pyproject.toml`
3. Installs Playwright browsers (Chromium + Firefox)
4. Installs pre-commit hooks
5. Creates `.env` from `.env.example`
6. Creates `data/` directories

**Time: ~5-15 minutes** (depends on internet speed)

---

## Step 3 — Add Your API Key

Edit `.env` and add your AI provider key:

```bash
nano .env
```

Find and set one of these:

```dotenv
# Option A: Claude (Anthropic) — Recommended
JARVIS_AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-api03-...

# Option B: OpenAI (GPT-4)
JARVIS_AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...

# Option C: No cloud — Local LLM (no API key, but slower)
JARVIS_AI_PROVIDER=local
JARVIS_AI_LOCAL_MODEL_PATH=/Users/you/models/llama-3-8b.gguf
```

**Get a Claude key:** https://console.anthropic.com → API Keys → Create Key

---

## Step 4 — Grant macOS Permissions

JARVIS controls your keyboard, microphone, and screen. macOS requires explicit permission for each.

```bash
bash scripts/grant_permissions.sh
```

This opens each System Settings panel automatically. Add **Terminal** to:
- ✅ Microphone
- ✅ Accessibility
- ✅ Screen Recording
- ✅ Full Disk Access

**These are one-time grants. You never need to do this again.**

---

## Step 5 — Pre-Download AI Models (Optional but Recommended)

Downloads all AI models so your first startup is instant instead of waiting 5 minutes.

```bash
source .venv/bin/activate
python3 scripts/download_models.py
```

Output:
```
[OK]  Whisper base.en model downloaded and cached ✓  (~145 MB)
[OK]  Wake word models downloaded ✓                   (~20 MB)
[OK]  TTS voice model downloaded ✓                   (~120 MB)
```

If you skip this, models download automatically on first `make dev`. Same result, just slower first startup.

---

## Step 6 — Run Pre-Flight Check

Verifies everything before you start:

```bash
bash scripts/preflight_check.sh
```

You want to see:
```
✓ Passed: 20+
⚠ Warnings: 4  (macOS permissions — shown as warnings, you just granted them)
✗ Failed: 0
✅ System is READY to run JARVIS OS!
```

Fix any ✗ failures before proceeding.

---

## Step 7 — Launch JARVIS

```bash
source .venv/bin/activate
make dev
```

You'll see:
```
[INFO] JARVIS OS starting...
[OK]   EventBus started
[OK]   Memory systems initialized
[OK]   AI provider: claude (claude-opus-4-5)
[OK]   Voice pipeline ready
[INFO] Say "Hey JARVIS" to begin...
```

The JARVIS window appears. **Say "Hey JARVIS"** and start talking.

---

## Voice Command Examples (Phase 1)

Once Phase 2 is built, you'll say things like:

| You say | JARVIS does |
|---------|-------------|
| "Hey JARVIS, open Chrome" | Launches Chrome |
| "Search for the latest Python tutorials" | Opens DuckDuckGo, extracts results |
| "Read my Downloads folder" | Lists files, summarizes recent ones |
| "Take a screenshot and describe what you see" | Captures screen, runs OCR + AI |
| "Type 'hello world' in the terminal" | Keyboard automation |
| "Remember that my AWS account ID is 123456" | Stores in long-term memory |
| "What did I ask you yesterday?" | Searches conversation history |

---

## Troubleshooting

### "Microphone not working"
1. System Settings → Privacy & Security → Microphone → add Terminal ✓
2. Restart Terminal
3. Test: `python3 -c "import pyaudio; p=pyaudio.PyAudio(); print('mic OK')"`

### "PyAudio install failed"
```bash
brew install portaudio
pip install pyaudio
```

### "Wake word not detecting"
- Speak clearly, in a quiet room
- Adjust sensitivity in `.env`: `JARVIS_VOICE_WAKE_SENSITIVITY=0.7` (higher = more sensitive)
- Test microphone is working first

### "No module named 'customtkinter'"
```bash
source .venv/bin/activate
pip install customtkinter
```

### "Playwright browsers not found"
```bash
source .venv/bin/activate
playwright install chromium firefox webkit
```

### Apple Silicon (M1/M2/M3) issues with PyAudio
```bash
# Make sure you're using the arm64 Python (not Rosetta)
python3 -c "import platform; print(platform.machine())"
# Should print: arm64

# If printing x86_64, use the arm64 Python:
brew install python@3.11
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Day-to-Day Usage

```bash
cd jarvis-os
source .venv/bin/activate
make dev          # start with verbose logging
# or
make run          # start in production mode
```

Stop JARVIS: `Ctrl+C` or say "Hey JARVIS, shut down"

---

## Updating JARVIS

When new code is added:
```bash
git pull
pip install -e ".[dev]"   # pick up new packages
make test                  # verify nothing broke
make dev                   # start
```
