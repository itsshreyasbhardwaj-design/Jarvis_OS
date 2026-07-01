# JARVIS OS

> *"Sometimes you gotta run before you can walk."* — Tony Stark

A production-grade, voice-controlled AI personal desktop assistant built on clean architecture principles. JARVIS is modular, extensible, and designed to execute complex multi-step tasks with user-approval gates at every sensitive action.

---

## ✨ Features (Phase 1 Foundation)

| Layer | Capability |
|-------|-----------|
| **AI** | Claude, OpenAI, Gemini, Local LLM — swap via config |
| **Voice** | Wake word → STT → AI → TTS pipeline |
| **Memory** | Short-term, long-term (SQLite/FTS5), vector store (ChromaDB) |
| **Desktop** | File navigation, keyboard/mouse, screen capture + OCR |
| **Browser** | Playwright-based search, extraction, automation |
| **Security** | Permission gates, audit logs, OS keychain credentials |
| **Plugins** | Dynamic plugin framework with isolated execution |
| **UI** | CustomTkinter dark theme with purple accent |

---

## 🏗️ Architecture

```
jarvis-os/
├── src/jarvis/
│   ├── core/          # Event bus, DI container, lifecycle
│   ├── ai/            # Provider abstraction, context, tool execution
│   ├── voice/         # Wake word, STT, TTS, audio pipeline
│   ├── memory/        # Short/long-term memory, vector store
│   ├── desktop/       # File system, keyboard, screen, apps
│   ├── browser/       # Playwright web automation
│   ├── security/      # Permissions, audit, credentials
│   ├── plugins/       # Plugin framework
│   ├── ui/            # Desktop UI + design system
│   ├── config/        # Pydantic settings
│   └── logging/       # Loguru structured logging
├── tests/             # Pytest test suite
├── docs/              # Architecture + development docs
├── scripts/           # Setup scripts
└── data/              # Runtime data (gitignored)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) (for voice)
- [Tesseract](https://tesseract-ocr.github.io/) (for OCR)
- An API key for at least one AI provider

### 1. Clone and set up

```bash
git clone https://github.com/your-org/jarvis-os.git
cd jarvis-os
bash scripts/setup.sh
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY (or OPENAI_API_KEY, etc.)
nano .env
```

### 3. Run

```bash
source .venv/bin/activate
make dev          # Development mode with verbose logging
# or
jarvis start      # Production mode
```

---

## ⚙️ Configuration

All configuration lives in `.env`. Key variables:

```dotenv
JARVIS_AI_PROVIDER=claude          # claude | openai | gemini | local
ANTHROPIC_API_KEY=sk-ant-...
JARVIS_SAFE_MODE=true              # Blocks HIGH/CRITICAL risk actions
JARVIS_WAKE_WORD=jarvis
JARVIS_ENV=development             # development | production
```

See `.env.example` for the full list with documentation.

---

## 🛠️ Development

```bash
make test          # Run all tests
make test-unit     # Unit tests only (fast)
make test-cov      # Tests + coverage report
make lint          # Ruff linter
make format        # Auto-format code
make type-check    # mypy strict check
make check         # All quality checks
```

### Adding a Plugin

```python
from jarvis.plugins.base import JarvisPlugin, PluginMetadata, PluginContext

class Plugin(JarvisPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="Does something useful",
            author="Your Name",
        )

    async def start(self, context: PluginContext) -> None:
        context.tool_executor.register(
            name="my_tool",
            description="Does something",
            parameters={"input": {"type": "string"}},
            required=["input"],
        )(self._my_tool)

    async def _my_tool(self, input: str) -> str:
        return f"Result: {input}"

    async def stop(self) -> None:
        pass
```

See [Plugin Development Guide](docs/plugins/plugin-development.md) for the full API.

---

## 🔒 Security Model

- All actions above `READ_ONLY` risk level require explicit user confirmation in `safe_mode=true`
- `HIGH` and `CRITICAL` actions are blocked entirely in safe mode
- Every action is written to an append-only audit log
- Credentials are stored in the OS keychain (never in `.env` for production)
- Forbidden paths (e.g. `/System`, `/etc`) cannot be accessed regardless of permissions

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture Overview](docs/architecture/system-overview.md) | System design and component relationships |
| [Development Setup](docs/development/setup.md) | Full setup guide |
| [Contributing](docs/development/contributing.md) | Contribution guidelines |
| [Plugin Development](docs/plugins/plugin-development.md) | Build and publish plugins |
| [Security Model](docs/security/security-model.md) | Permission system deep-dive |
| [Roadmap](docs/roadmap/ROADMAP.md) | What's coming next |

---

## 🗺️ Roadmap

**Phase 1 (Current):** Foundation — event bus, DI, AI providers, voice pipeline, memory, desktop automation, browser, security, plugins, UI, logging, testing.

**Phase 2:** Feature depth — calendar, email, web research, code execution, file summarisation, notification centre.

**Phase 3:** Intelligence — long-running tasks, learning user preferences, multi-agent coordination.

**Phase 4:** Distribution — packaging, auto-update, marketplace plugins, cross-platform.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ and ambition. JARVIS OS is a personal project, not affiliated with Marvel or Iron Man.*
