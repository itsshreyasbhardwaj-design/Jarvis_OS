# JARVIS OS — Claude Code Master Context

> This file is auto-read by Claude Code on every session. It contains everything needed
> to work on JARVIS OS without reading the prior conversation history.

---

## ⚠️ CRITICAL — ALWAYS LAUNCH LIKE THIS

```bash
# Option A — wrapper script (recommended):
bash run_claude.sh

# Option B — inline env vars:
ANTHROPIC_BASE_URL=http://127.0.0.1:6767 ANTHROPIC_MODEL=claude-opus-4-8 claude

# Option C — permanent fix (run once):
echo 'export ANTHROPIC_BASE_URL=http://127.0.0.1:6767' >> ~/.zshrc && source ~/.zshrc
```

**Never run bare `claude`** — Headroom requires `ANTHROPIC_BASE_URL=http://127.0.0.1:6767`.  
**Always use model:** `claude-opus-4-8` (ultracode / Opus 4.8).

---

## What This Project Is

**JARVIS OS** is a production-grade AI personal desktop assistant for macOS, inspired by
Iron Man's JARVIS. It is voice-controlled, event-driven, plugin-extensible, and built to
run locally on Apple Silicon (M-series). Phase 1 (the complete foundation) is **done**.

**Owner:** Shrey (shreyas.b.hlc0004@gmail.com)  
**Stack:** Python 3.11+, async-first, SOLID principles, full type hints throughout  
**Platform:** macOS (Apple Silicon primary, Intel fallback)

---

## Phase Status

| Phase | Status | Contents |
|---|---|---|
| **Phase 1 — Foundation** | ✅ COMPLETE | Event bus, DI, lifecycle, providers, memory, security scaffolding |
| **Phase 2 — Runnable brain** | ✅ WORKING | Text assistant: memory (SQLite) + LLM router (Claude via litellm, offline fallback) + tools (web search, files, system, time), wired into `python -m jarvis` and `jarvis chat`. 68 tests passing. |
| **Phase 2 — Voice + UI** | 🔲 Next | "Hey JARVIS" wake/STT/TTS + Qt window — needs the native stack (sherpa-onnx, PySide6, mic, display) |
| **Phase 3 — Autonomy** | 🔲 Future | Long-running tasks, multi-agent, proactive assistance |
| **Phase 4 — Distribution** | 🔲 Future | Packaging, auto-update, plugin marketplace |

> **What actually runs today (July 2026):** Python 3.12 venv via `uv` (this Mac has no Homebrew / only system 3.9). Launch with `Talk to JARVIS.command` or `./jarvis chat`. Works offline; add `ANTHROPIC_API_KEY` to `.env` for live Claude. The original docs describe an aspirational full system — treat the table above as ground truth. See `HOW_TO_USE.md`.

---

## Technology Stack (Audited June 2026 — v2)

Every choice below was verified against GitHub star counts, license status, and Apple
Silicon compatibility. Do not substitute without updating `docs/technology-audit.md`.

### Voice Pipeline
| Role | Package | Why |
|---|---|---|
| STT | `RealtimeSTT` | Streaming VAD + whisper.cpp Metal acceleration on M-series |
| Wake word | `sherpa-onnx` | Apache-2.0, CoreML backend, ~160ms latency |
| TTS engine | `RealtimeTTS` | Feeds LLM token streams → speaks before generation finishes |
| TTS model | `kokoro` | Apache-2.0, 82M params, ~150ms, near-ElevenLabs quality |
| TTS fallback | `edge-tts` | Online, zero API key, 400+ Microsoft neural voices |
| Audio I/O | `sounddevice` | PortAudio, non-blocking callbacks, lowest latency |

> ⚠️ `faster-whisper` (CPU-only on macOS), `coqui-ai/TTS` (archived), `openwakeword`
> (CC BY-NC-SA non-commercial) are all **replaced**. Do not re-add them.

### AI & LLM
| Role | Package | Why |
|---|---|---|
| Unified LLM router | `litellm` | Swap Claude/GPT/Ollama/MLX via config, no code change |
| Primary SDK | `anthropic` | Claude — direct SDK for Claude-specific features |
| Structured output | `instructor` | Typed Pydantic from any LLM, auto-retry on validation |
| Local inference | `mlx-lm` (optional) | ~130 tok/s on M4 Pro — 3× faster than llama.cpp |
| Alt local | `ollama` | OpenAI-compatible, good DX, uses MLX on Apple Silicon |

### Memory & Storage
| Role | Package | Why |
|---|---|---|
| Vector DB | `lancedb` | Rust-backed HNSW, hybrid vector+FTS, no server, fast |
| Embeddings | `fastembed` | ONNX, 80 MB RAM, no PyTorch dep, fast cold start |
| Conversation DB | `aiosqlite` | Async SQLite for history, preferences, audit log |

### Desktop Automation
| Role | Package | Why |
|---|---|---|
| Accessibility | `atomacos` | macOS AX API — click by label/role, works on all native apps |
| Keyboard/mouse | `pynput` | CGEvent-based, macOS arm64, monitoring + synthesis |
| Screen capture | `mss` | 30+ FPS multi-monitor, minimal CPU |
| OCR (UI/screen) | `pyobjc-framework-Vision` | Apple Vision — Neural Engine, zero download, built-in |
| OCR (documents) | `surya-ocr` (optional) | 83.3% olmOCR-bench, Metal backend |

> ⚠️ `pyautogui` is **replaced** (ignored by native macOS apps).
> ⚠️ `pytesseract`/Tesseract is **replaced** (Apple Vision is faster and built-in).

### UI
| Role | Package | Why |
|---|---|---|
| Window/widgets | `PySide6` | Qt6, LGPL, native macOS dark mode, universal2 wheels |
| Real-time viz | `pyqtgraph` | OpenGL 60fps waveform inside Qt widget tree |
| Async bridge | `qasync` | Merges asyncio into Qt event loop, one line |
| Dark theme | `pyqtdarktheme` | Syncs with macOS accent color |

> ⚠️ `customtkinter` is **replaced** (Tk-based, cannot do 60fps GPU waveform).

### Infrastructure
| Role | Package | Why |
|---|---|---|
| CLI | `typer` | Vendors click, type-hint native, drop-in upgrade |
| Scheduler | `apscheduler` v4 | Async-native cron/interval/one-shot |
| Notifications | `rumps` | macOS menu bar + native notifications |
| HTTP | `httpx` | HTTP/2, sync+async, best DX |
| Config | `pydantic-settings` | Type-safe env vars + `.env` loading |
| Logging | `loguru` | Zero-config, colorized, enqueue=True for thread safety |
| Security | `keyring` + `cryptography` | OS keychain + crypto primitives |

---

## Repository Layout

```
jarvis-os/
├── CLAUDE.md                  ← YOU ARE HERE
├── README.md
├── QUICKSTART.md              ← Zero-to-voice in 7 steps
├── pyproject.toml             ← All dependencies + tool config
├── Makefile
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml             ← Matrix: Python 3.11+3.12, ubuntu+macos
│       └── lint.yml           ← Standalone ruff check
│
├── src/jarvis/
│   ├── __init__.py
│   ├── main.py                ← Entry point: build DI container → start()
│   ├── orchestrator.py        ← JarvisOrchestrator: wires all subsystems
│   │
│   ├── core/                  ← Foundation (no deps on other modules)
│   │   ├── event_bus.py       ← Async priority EventBus, fnmatch patterns
│   │   ├── service_registry.py ← DI container, singleton resolution
│   │   └── lifecycle.py       ← Priority startup/shutdown, health checks
│   │
│   ├── ai/                    ← AI provider abstraction
│   │   ├── providers/
│   │   │   ├── base.py        ← AIProvider ABC
│   │   │   ├── claude.py      ← Anthropic/Claude implementation
│   │   │   ├── openai.py      ← OpenAI implementation
│   │   │   ├── gemini.py      ← Gemini implementation
│   │   │   └── local.py       ← litellm → mlx-lm / ollama
│   │   ├── tool_executor.py   ← @register decorator, permission gate, timeout
│   │   └── context_manager.py ← 100k token sliding window, pinned messages
│   │
│   ├── voice/                 ← Voice pipeline
│   │   ├── wake_word/
│   │   │   └── detector.py    ← sherpa-onnx KeywordSpotter, CoreML
│   │   ├── stt/
│   │   │   └── transcriber.py ← RealtimeSTT wrapper
│   │   ├── tts/
│   │   │   └── synthesizer.py ← RealtimeTTS wrapper (kokoro + edge-tts)
│   │   └── audio_pipeline.py  ← State machine: IDLE→WAKE→RECORD→STT→AI→TTS
│   │
│   ├── memory/                ← Multi-tier memory system
│   │   ├── short_term.py      ← deque with maxlen
│   │   ├── long_term.py       ← aiosqlite + FTS5 full-text search
│   │   ├── knowledge_store.py ← lancedb vector store + fastembed
│   │   ├── conversation.py    ← SQLite conversation history
│   │   └── preferences.py     ← User preferences (JSON)
│   │
│   ├── desktop/               ← Desktop automation
│   │   ├── controller.py      ← atomacos + pynput safe wrappers
│   │   ├── screen_capture.py  ← mss multi-monitor capture
│   │   ├── ocr.py             ← Apple Vision (pyobjc-framework-Vision)
│   │   └── window_manager.py  ← NSWorkspace + Quartz window info
│   │
│   ├── browser/               ← Browser automation
│   │   ├── controller.py      ← Playwright async wrapper
│   │   └── extractor.py       ← BeautifulSoup + lxml content extraction
│   │
│   ├── security/              ← Permission + audit layer
│   │   ├── permissions.py     ← RiskLevel, PermissionManager, safe_mode
│   │   ├── audit.py           ← Append-only JSONL AuditLogger
│   │   └── credentials.py     ← keyring OS keychain wrapper
│   │
│   ├── plugins/               ← Plugin framework
│   │   ├── base.py            ← JarvisPlugin ABC, PluginMetadata
│   │   ├── registry.py        ← Dynamic loader, looks for class named Plugin
│   │   └── examples/          ← Reference plugin implementations
│   │
│   ├── config/
│   │   └── settings.py        ← Pydantic Settings with all sub-models
│   │
│   ├── ui/
│   │   ├── design_system.py   ← JarvisColors, JarvisTypography, PySide6 theme
│   │   ├── main_window.py     ← MainWindow (520×680, dark, PySide6)
│   │   └── widgets/           ← VoiceWaveform (pyqtgraph), ChatBubble, etc.
│   │
│   └── logging/
│       └── setup.py           ← Loguru: console + JSON file + perf log
│
├── tests/
│   ├── conftest.py            ← Shared fixtures: event_bus, mock_ai, memory, etc.
│   ├── unit/
│   │   ├── test_core/         ← EventBus, ServiceRegistry tests
│   │   ├── test_ai/           ← Provider, context manager tests
│   │   ├── test_memory/       ← Short/long term memory tests
│   │   └── test_security/     ← Permission, audit log tests
│   └── integration/           ← (Phase 2) end-to-end pipeline tests
│
├── docs/
│   ├── technology-audit.md    ← Library decisions with GitHub star counts
│   ├── architecture/
│   │   ├── system-overview.md
│   │   ├── component-diagram.md
│   │   └── data-flow.md
│   ├── development/
│   │   ├── setup.md
│   │   ├── contributing.md
│   │   └── coding-standards.md
│   ├── security/security-model.md
│   ├── plugins/plugin-development.md
│   ├── api/api-reference.md
│   └── roadmap/ROADMAP.md
│
└── scripts/
    ├── install_macos.sh       ← Homebrew deps: ffmpeg, portaudio, llama.cpp, etc.
    ├── setup.sh               ← venv + pip install
    ├── preflight_check.sh     ← System check: PASS/WARN/FAIL before first run
    ├── download_models.py     ← Pre-cache Whisper + Kokoro + sherpa-onnx
    └── grant_permissions.sh   ← Opens macOS Privacy panels
```

---

## Architecture Rules (NEVER Violate)

### 1. Module Dependency Graph
```
core → (no deps)
ai → core
voice → core
memory → core
desktop → core, security
browser → core, security
security → core
plugins → core, security
config → (no deps)
ui → core, config
```

**Cross-module imports are FORBIDDEN.** Modules communicate ONLY via the EventBus.
If module A needs module B's output, A subscribes to B's events. Never `import jarvis.memory` from `jarvis.desktop`.

### 2. Async-First
- Every I/O method must be `async def`
- Use `asyncio.to_thread()` for blocking calls (audio, OS APIs)
- Use `asyncio.TaskGroup` for parallel operations (Python 3.11+)
- Never use `time.sleep()` — use `await asyncio.sleep()`
- Never use `open()` for files — use `aiofiles.open()`

### 3. Permission Gate (Always)
```python
# Before ANY sensitive action:
allowed = await self._permissions.check(
    action="describe_what_you_are_doing",
    risk_level=RiskLevel.MEDIUM,
    details={"target": "..."},
)
if not allowed:
    return  # User denied or safe_mode blocked it
```

### 4. Type Hints — 100% Coverage
```python
# CORRECT
async def transcribe(self, audio: bytes) -> TranscriptionResult:
    ...

# WRONG (mypy strict will fail)
async def transcribe(self, audio):
    ...
```

### 5. Error Handling
```python
# CORRECT — specific exceptions, logged, re-raised or handled
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error("Operation failed: {}", e)
    raise JarvisOperationError(f"Could not complete: {e}") from e

# WRONG — bare except
try:
    result = await risky_operation()
except:
    pass
```

### 6. Logging — Loguru Style
```python
# CORRECT — lazy evaluation (no f-strings in logger calls)
logger.info("User said: {}", transcription.text)
logger.debug("Processing {} tokens", token_count)

# WRONG
logger.info(f"User said: {transcription.text}")  # eager, wasted if filtered
```

---

## Core Patterns (Copy-Paste Reference)

### Publishing an Event
```python
await self._event_bus.publish(
    "jarvis.voice.transcription_complete",
    data={"text": transcription.text, "confidence": 0.97},
)
```

### Subscribing to Events
```python
# In a module's start() method:
await self._event_bus.subscribe(
    "jarvis.voice.*",          # fnmatch pattern
    self._on_voice_event,
)

async def _on_voice_event(self, event: Event) -> None:
    text = event.data.get("text", "")
    ...
```

### Registering a Tool
```python
@tool_executor.register(
    name="open_application",
    description="Open a macOS application by name",
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    requires_confirmation=False,
)
async def open_application(app_name: str) -> ToolResult:
    ...
```

### Writing a Plugin
```python
# plugins/my_plugin/plugin.py
from jarvis.plugins.base import JarvisPlugin, PluginMetadata, PluginContext

class Plugin(JarvisPlugin):  # Must be named exactly "Plugin"
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="What this plugin does",
            author="Your Name",
        )

    async def start(self, context: PluginContext) -> None:
        context.tool_executor.register(...)  # register tools
        await context.event_bus.subscribe("jarvis.*", self._handler)

    async def stop(self) -> None:
        ...  # cleanup
```

### Using litellm (LLM Router)
```python
from litellm import acompletion

# Switch provider via JARVIS_AI_PROVIDER env var — no code change
response = await acompletion(
    model=settings.ai.model,     # e.g. "anthropic/claude-sonnet-4-6"
    messages=messages,
    stream=True,
)
```

### Using RealtimeTTS (Stream → Speak)
```python
from RealtimeTTS import TextToAudioStream, KokoroEngine

engine = KokoroEngine()
stream = TextToAudioStream(engine)

# Feed Claude's streaming response — speaks while generating
stream.feed(claude_streaming_generator)
stream.play_async()
```

---

## Environment Variables (.env)

```bash
# AI Provider (change to switch LLM backend — no code changes needed)
JARVIS_AI_PROVIDER=anthropic          # anthropic | openai | gemini | local
JARVIS_AI_MODEL=claude-sonnet-4-6     # exact model string

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Voice
JARVIS_VOICE_WAKE_WORD=hey jarvis
JARVIS_VOICE_STT_MODEL=distil-large-v3
JARVIS_VOICE_TTS_ENGINE=kokoro        # kokoro | edge-tts | pyttsx3
JARVIS_VOICE_TTS_VOICE=af_heart

# Security
JARVIS_SECURITY_SAFE_MODE=true        # blocks HIGH+ risk actions without approval
JARVIS_SECURITY_REQUIRE_CONFIRMATION=true

# UI
JARVIS_UI_THEME=dark
JARVIS_UI_WINDOW_OPACITY=0.97

# Logging
JARVIS_LOG_LEVEL=INFO
JARVIS_LOG_FORMAT=pretty              # pretty | json
JARVIS_LOG_FILE=~/.jarvis/logs/jarvis.log
```

---

## Commands Reference

```bash
# Setup
bash scripts/install_macos.sh    # Install Homebrew deps (run once)
bash scripts/setup.sh            # Create venv + pip install
python3 scripts/download_models.py   # Pre-cache AI models (~1.1 GB)
bash scripts/grant_permissions.sh    # Open macOS Privacy panels
bash scripts/preflight_check.sh      # Verify everything is ready

# Development
make dev                         # Start JARVIS (hot-reload)
make test                        # pytest tests/unit/ (fast, CI)
make test-all                    # All tests including integration
make lint                        # ruff check + mypy
make format                      # ruff format + black
make typecheck                   # mypy --strict
make coverage                    # pytest + HTML coverage report

# Quality gates (must pass before any commit)
make lint && make typecheck && make test

# Build
make clean                       # Remove __pycache__, .pytest_cache
make build                       # Build distributable wheel
```

---

## Security Model

```
RiskLevel.READ_ONLY = 0  → Always allowed
RiskLevel.LOW       = 1  → Always allowed
RiskLevel.MEDIUM    = 2  → Allowed, logged
RiskLevel.HIGH      = 3  → Requires user confirmation (blocked in safe_mode)
RiskLevel.CRITICAL  = 4  → Always requires explicit approval
```

**Forbidden paths** (PermissionManager blocks all access):
`/System`, `/usr/bin`, `/bin`, `/sbin`, `~/.ssh`, `~/.aws`, `~/.gnupg`

**Audit log:** Every action written to `~/.jarvis/audit/audit.log` (JSONL, append-only).

---

## Key Design Patterns

### EventBus (core/event_bus.py)
- Async priority queue (0=critical, 9=low)
- fnmatch pattern subscriptions (`"jarvis.voice.*"`)
- Handler isolation — one crashing handler never stops others
- Dead letter queue for unhandled events
- `subscribe_once()` for one-shot listeners

### Service Registry (core/service_registry.py)
- Singleton resolution via type
- Circular dependency detection
- Auto-wire via `inspect.signature`
- Lazy initialization

### Lifecycle Manager (core/lifecycle.py)
- Priority-ordered startup: 0-9 core → 10-19 security → 20-29 memory → 30+ features
- Health checks per module
- Graceful shutdown in reverse priority order

### Context Window (ai/context_manager.py)
- Max 100k tokens, target 80k
- Sliding window eviction (oldest non-pinned messages)
- Pinned messages (system prompt, important context) never evicted

---

## Testing Conventions

```python
# All tests are async
@pytest.mark.asyncio
async def test_something(event_bus, mock_ai_provider):  # fixtures from conftest.py
    ...

# Key fixtures (from tests/conftest.py):
# event_bus         — started/stopped per test
# service_registry  — clean registry
# test_settings     — no .env loaded
# mock_ai_provider  — MagicMock with AsyncMock
# short_term_memory — in-memory deque
# long_term_memory  — tmp_path SQLite
# permissive_permissions — auto-approve, safe_mode=False
# restricted_permissions — safe_mode=True
# temp_workspace    — tmp_path with sample files

# Markers:
# @pytest.mark.unit
# @pytest.mark.integration
# @pytest.mark.slow
# @pytest.mark.voice       (requires audio hardware)
# @pytest.mark.desktop     (requires display)
# @pytest.mark.apple_silicon (requires mlx-lm)
```

---

## Common Tasks for Claude Code

### Adding a New Tool
1. Add `@tool_executor.register(...)` decorated function in the relevant module
2. Set appropriate `risk_level`, `timeout`, and `requires_confirmation`
3. Return `ToolResult(success=True/False, data={...}, error=None)`
4. Add unit test in `tests/unit/test_ai/test_tool_executor.py`

### Adding a New Voice Command Handler
1. Subscribe to `"jarvis.voice.transcription_complete"` in your module's `start()`
2. Parse intent from `event.data["text"]`
3. Call appropriate tool via `tool_executor.execute()`
4. Return result — the orchestrator publishes to TTS automatically

### Adding a New Memory Type
1. Create class in `src/jarvis/memory/`
2. Implement `store()`, `search()`, `clear()` async methods
3. Register in `ServiceRegistry` at lifecycle priority 20-29
4. Add to `LifecycleManager` with `health_check`

### Creating a Plugin
1. `mkdir src/jarvis/plugins/my_plugin/`
2. Create `plugin.py` with `class Plugin(JarvisPlugin):`
3. Create `__init__.py` and `plugin.json` (metadata)
4. Install: `jarvis plugin install ./src/jarvis/plugins/my_plugin/`
5. See `docs/plugins/plugin-development.md` for full guide

### Switching the AI Backend
```bash
# In .env — no code changes needed
JARVIS_AI_PROVIDER=local
JARVIS_AI_MODEL=ollama/llama3.2    # or mlx/mistral-7b
```

---

## What NOT to Do

```python
# ❌ Synchronous I/O in async code
with open("file.txt") as f:          # blocks event loop
    data = f.read()

# ✅ Correct
async with aiofiles.open("file.txt") as f:
    data = await f.read()

# ❌ Cross-module import
from jarvis.memory import LongTermMemory  # in jarvis.desktop

# ✅ Correct — use event bus
await self._event_bus.publish("jarvis.memory.store_request", data={...})

# ❌ Missing permission check for sensitive action
await controller.click(button)

# ✅ Correct
if await self._permissions.check("click_ui_element", RiskLevel.LOW):
    await controller.click(button)

# ❌ Logging with f-string
logger.info(f"Result: {result}")

# ✅ Correct
logger.info("Result: {}", result)

# ❌ Bare exception
except Exception:
    pass

# ✅ Correct
except SpecificError as e:
    logger.error("Failed: {}", e)
    raise

# ❌ Skipping type hints
def process(data):
    return data

# ✅ Correct
def process(data: dict[str, Any]) -> ProcessedResult:
    return ProcessedResult(data)
```

---

## Phase 2 — What to Build Next

See `docs/roadmap/ROADMAP.md` for full detail. Key Phase 2 items:

1. **Calendar integration** — read/create Google Calendar events via voice
2. **Email management** — read, summarize, draft, send via voice
3. **Web research** — voice-triggered search + summarization pipeline
4. **Code execution** — sandboxed Python/shell execution with output capture
5. **File management** — voice-controlled finder, rename, move, search
6. **System monitoring** — CPU, RAM, disk, network status on demand
7. **Clipboard intelligence** — detect and act on clipboard content
8. **Meeting assistant** — join, transcribe, summarize meetings

When starting Phase 2 work, read `docs/architecture/data-flow.md` first to understand
the event flow before adding new modules.

---

## Troubleshooting & Known Issues

### Headroom Proxy Error (Claude Code)

**Error:** `ANTHROPIC_BASE_URL is not http://127.0.0.1:6767; Claude is not routing through Headroom`

**Cause:** Headroom app intercepts Claude API calls and requires Claude Code to route through its local proxy.

**Fix (permanent — run once):**
```bash
echo 'export ANTHROPIC_BASE_URL=http://127.0.0.1:6767' >> ~/.zshrc
source ~/.zshrc
```

**Fix (per-session):**
```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:6767
claude
```

**Best practice — always launch Claude Code via:**
```bash
bash run_claude.sh    # sets env + activates venv + launches claude
```

The `run_claude.sh` in the project root handles this automatically.

### Claude Code not found
```bash
npm install -g @anthropic-ai/claude-code
```

### Python version error (need 3.11+)
```bash
brew install python@3.11
python3.11 -m venv .venv
source .venv/bin/activate
```

### wake word model missing
```bash
python3 scripts/download_models.py
```
