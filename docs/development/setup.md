# Development Setup

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Runtime |
| ffmpeg | Any | Audio processing for voice pipeline |
| Tesseract | 4+ | OCR for screen capture |
| Git | 2+ | Version control |
| macOS / Linux | — | Supported platforms |

### Installing Prerequisites

**macOS (Homebrew):**
```bash
brew install python@3.11 ffmpeg tesseract portaudio
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv ffmpeg tesseract-ocr                  portaudio19-dev python3-pyaudio libnotify-dev
```

---

## Automated Setup (Recommended)

```bash
git clone https://github.com/your-org/jarvis-os.git
cd jarvis-os
bash scripts/setup.sh
```

This script:
1. Checks Python 3.11+ is installed
2. Creates `.venv/` virtual environment
3. Installs all production + dev dependencies
4. Installs Playwright browsers (Chromium, Firefox)
5. Installs pre-commit hooks
6. Creates `.env` from `.env.example`
7. Creates `data/` directory structure

---

## Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# 3. Install Playwright browsers
playwright install chromium firefox webkit

# 4. Install pre-commit hooks
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 6. Create data directories
mkdir -p data/{logs,memory/{short_term,long_term,vector_store},models,audit,plugins}
```

---

## API Keys

Edit `.env` and add at least one AI provider key:

```dotenv
# Option 1: Claude (Recommended)
ANTHROPIC_API_KEY=sk-ant-...
JARVIS_AI_PROVIDER=claude

# Option 2: OpenAI
OPENAI_API_KEY=sk-...
JARVIS_AI_PROVIDER=openai

# Option 3: Local LLM (no API key needed)
JARVIS_AI_PROVIDER=local
JARVIS_AI_LOCAL_MODEL_PATH=/path/to/model.gguf
```

---

## Verify Setup

```bash
source .venv/bin/activate
make verify
```

Expected output:
```
✓ Python version OK
✓ Package imports OK
All checks passed!
```

---

## Running JARVIS

```bash
# Development mode (verbose logging)
make dev

# Production mode
make run

# CLI
jarvis start
jarvis health
jarvis config
```

---

## Common Issues

**`ModuleNotFoundError: No module named 'pyaudio'`**
Install system audio libraries first:
```bash
# macOS
brew install portaudio
pip install pyaudio

# Linux
sudo apt install portaudio19-dev
pip install pyaudio
```

**`tesseract: command not found`**
```bash
brew install tesseract        # macOS
sudo apt install tesseract-ocr  # Linux
```

**`playwright._impl._errors.Error: Executable doesn't exist`**
```bash
playwright install chromium
```
