# JARVIS OS — Build Context (Full Session History)

This file captures everything built across all Cowork/Claude sessions.
Claude Code should read CLAUDE.md first (architecture + patterns).
Read this file only when you need to understand WHY something was built a certain way.

---

## What Was Built (Phase 1 — All 17 Tasks Complete)

### Task 1-2: Project Foundation
- Enterprise directory structure: `src/jarvis/{core,ai,voice,memory,desktop,browser,security,plugins,config,ui,logging}/`
- `pyproject.toml` with full dependency spec, ruff/mypy/pytest/coverage config
- `Makefile` with dev/test/lint/typecheck/build targets
- `.env.example` with all configurable variables
- `.github/workflows/ci.yml` (matrix: Python 3.11+3.12, ubuntu+macOS)
- `.github/workflows/lint.yml` (standalone ruff check)
- `pytest.ini`, `pre-commit` config, `.gitignore`

### Task 3: Core Module
Built the foundation all other modules depend on:
- **EventBus** (`core/event_bus.py`): Async priority queue, fnmatch subscriptions, handler isolation, dead letter queue, `subscribe_once()`, stats dict
- **ServiceRegistry** (`core/service_registry.py`): Singleton DI container, circular dep detection, auto-wire via `inspect.signature`
- **LifecycleManager** (`core/lifecycle.py`): Priority startup (0-9 core → 10-19 security → 20-29 memory → 30+ features), health checks, reverse-order shutdown
- **JarvisOrchestrator** (`orchestrator.py`): Wires all subsystems, handles voice input → AI → TTS loop

### Task 4: AI Layer
- **AIProvider ABC** (`ai/providers/base.py`): `complete()`, `stream()`, `count_tokens()`, `health_check()`
- **Claude** (`ai/providers/claude.py`): anthropic SDK, streaming, tool use, extended thinking
- **OpenAI** (`ai/providers/openai.py`): GPT-4o, function calling, streaming
- **Gemini** (`ai/providers/gemini.py`): google-generativeai, streaming
- **Local** (`ai/providers/local.py`): litellm → mlx-lm / ollama routing
- **ToolExecutor** (`ai/tool_executor.py`): `@register` decorator, permission gate, `asyncio.wait_for` timeout, parallel `gather` execution, `ToolResult`
- **ContextManager** (`ai/context_manager.py`): 100k token sliding window, 80k target, pinned messages, `add_message/get_context`
- **System prompt** (`ai/prompts.py`): `build_jarvis_system_prompt()` with persona, date, tools, safety

### Task 5: Voice Infrastructure
- **WakeWordDetector** (`voice/wake_word/detector.py`): sherpa-onnx KeywordSpotter, CoreML provider, configurable phrase
- **SpeechTranscriber** (`voice/stt/transcriber.py`): RealtimeSTT wrapper, streaming, `TranscriptionResult`
- **TextToSpeechSynthesizer** (`voice/tts/synthesizer.py`): RealtimeTTS wrapper, kokoro engine, edge-tts fallback, `stop_speaking()`
- **AudioPipeline** (`voice/audio_pipeline.py`): Full state machine: IDLE → LISTENING → RECORDING → TRANSCRIBING → THINKING → SPEAKING. RMS-VAD recording, interruption support, sounddevice for I/O

### Task 6: Memory System
- **ShortTermMemory** (`memory/short_term.py`): `deque(maxlen=100)`, FIFO eviction, `get_recent(n)`, `search()`, `is_full` property
- **LongTermMemory** (`memory/long_term.py`): aiosqlite + FTS5, `store(content, importance)`, `search(query)`, `get_important(threshold)`
- **KnowledgeStore** (`memory/knowledge_store.py`): lancedb + fastembed, `add(text, metadata)`, `search(query, top_k)`, hybrid vector+FTS
- **ConversationHistory** (`memory/conversation.py`): SQLite, `add_message`, `get_history(session_id)`, `clear_session()`
- **UserPreferences** (`memory/preferences.py`): JSON file, `get(key, default)`, `set(key, value)`, `reset()`

### Task 7: Desktop Automation
- **DesktopController** (`desktop/controller.py`): atomacos AX API, pynput keyboard/mouse, safe wrappers with permission gate
- **ScreenCapture** (`desktop/screen_capture.py`): mss multi-monitor, `capture_region()`, `capture_active_window()`
- **OCR** (`desktop/ocr.py`): Apple Vision (pyobjc-framework-Vision), `extract_text(image)`, `find_text_location(image, text)`
- **WindowManager** (`desktop/window_manager.py`): NSWorkspace + Quartz, `get_active_app()`, `get_window_list()`, `focus_window(title)`

### Task 8: Browser Automation
- **BrowserController** (`browser/controller.py`): Playwright async, `navigate(url)`, `click(selector)`, `type_text()`, `screenshot()`, `wait_for_element()`
- **ContentExtractor** (`browser/extractor.py`): BeautifulSoup + lxml, `extract_main_content(html)`, `extract_links()`, `summarize_page()`

### Task 9: Security Layer
- **PermissionManager** (`security/permissions.py`): `RiskLevel` IntEnum (0-4), `check(action, risk_level)`, `check_path(path)`, `safe_mode`, forbidden paths, `action_history`
- **AuditLogger** (`security/audit.py`): Append-only JSONL, `log_action(action, risk, approved, details)`, `read_entries()`, `session_id`
- **CredentialStore** (`security/credentials.py`): OS keychain via `keyring`, `store(service, key, value)`, `retrieve(service, key)`, `delete(service, key)`

### Task 10: Plugin Framework
- **JarvisPlugin ABC** (`plugins/base.py`): `metadata`, `start(context)`, `stop()`, `on_error(e)`, `is_running`
- **PluginContext**: `tool_executor`, `event_bus`, `data_dir`, `config`
- **PluginRegistry** (`plugins/registry.py`): Dynamic loader (looks for `class Plugin`), `load(path)`, `unload(name)`, `list_plugins()`
- **Example plugins**: weather, notes, timer (in `plugins/examples/`)

### Task 11: Configuration
- **Settings** (`config/settings.py`): Pydantic v2 BaseSettings, nested sub-models: `AISettings`, `VoiceSettings`, `MemorySettings`, `SecuritySettings`, `UISettings`, `LogSettings`
- All settings loadable from `.env` with `JARVIS_` prefix

### Task 12: UI Foundation
- **JarvisColors** (`ui/design_system.py`): `#0A0A0F` bg, `#7C3AED` accent, full palette
- **JarvisTypography**: Inter + JetBrains Mono, PySide6 QFont
- **MainWindow** (`ui/main_window.py`): 520×680, PySide6, dark theme, qasync event loop
- **VoiceWaveform** widget: pyqtgraph OpenGL, 60fps real-time audio visualization
- **ChatBubble** widget: message bubbles with timestamps
- **StatusBar** widget: pipeline state indicator

### Task 13: Testing & CI
- `tests/conftest.py`: fixtures: `event_bus`, `service_registry`, `test_settings`, `mock_ai_provider`, `short_term_memory`, `long_term_memory`, `permissive_permissions`, `restricted_permissions`, `temp_workspace`
- `tests/unit/test_core/test_event_bus.py`: subscribe, wildcard, once, crash-isolation, stats
- `tests/unit/test_ai/test_providers.py`: Message/Role, TokenUsage, AIResponse, mock provider
- `tests/unit/test_memory/test_short_term.py`: add/retrieve, FIFO eviction, search, is_full
- `tests/unit/test_security/test_permissions.py`: READ_ONLY, HIGH safe_mode, forbidden path
- `.github/workflows/ci.yml`: matrix 3.11+3.12, ubuntu+macos, lint+test+security jobs

### Task 14: Documentation
- `README.md`: features table, arch tree, quick start, config table, make commands, plugin example, security model, roadmap
- `docs/architecture/`: system-overview, component-diagram, data-flow (end-to-end voice command path)
- `docs/development/`: setup, contributing (branching strategy, conventional commits), coding-standards
- `docs/security/security-model.md`: RiskLevel, safe_mode, forbidden paths, audit log format
- `docs/plugins/plugin-development.md`: full plugin tutorial with PluginContext API
- `docs/api/api-reference.md`: EventBus, AIProvider, ToolExecutor, PermissionManager, LongTermMemory, KnowledgeStore, JarvisPlugin, AuditLogger APIs
- `docs/roadmap/ROADMAP.md`: Phase 1 (done), Phase 2-4 (planned)

### Task 15: Verification
- Fixed `src/jarvis/logging/setup.py` line 49: JSON format string had mismatched quotes (SyntaxError)
- Fixed `src/jarvis/voice/audio_pipeline.py` line 187: nested double-quotes in f-string (SyntaxError)
- Final: **92 Python files, 0 syntax errors, 6,563 source LOC**

### Task 16: Pre-Flight System
- `scripts/install_macos.sh`: Homebrew deps (ffmpeg, portaudio, llama.cpp, cmake, libomp)
- `scripts/preflight_check.sh`: PASS/WARN/FAIL check (Python, packages, models, macOS permissions, disk space)
- `scripts/download_models.py`: Pre-caches Whisper (distil-large-v3) + Kokoro + sherpa-onnx
- `scripts/grant_permissions.sh`: Opens macOS Privacy panels (Microphone, Accessibility, Screen Recording, Full Disk)
- `QUICKSTART.md`: Zero-to-voice in 7 steps

### Task 17: GitHub Library Audit
- Ran 8 parallel research sweeps across all JARVIS components (June 2026)
- Produced `docs/technology-audit.md` with star counts, license status, Apple Silicon compatibility
- **9 replacements**: faster-whisper→RealtimeSTT, Coqui→RealtimeTTS+kokoro, openwakeword→sherpa-onnx, pyautogui→atomacos+pynput, pytesseract→pyobjc-Vision, chromadb→lancedb, customtkinter→PySide6+pyqtgraph, click→typer, pync+schedule→rumps+apscheduler
- **3 additions**: litellm (LLM router), instructor (typed outputs), mlx-lm (optional, Apple Silicon native)
- Updated `pyproject.toml` with all changes + full inline documentation

---

## Bugs Fixed During Build

1. **`src/jarvis/logging/setup.py` line 49** — JSON format string used `"{{"time"..."` with mismatched quotes. Fixed to single-quoted string.
2. **`src/jarvis/voice/audio_pipeline.py` line 187** — `f"User said: "{text}""` nested double quotes. Fixed to `logger.info('User said: "{}"', text)`.
3. **Zip creation** — `zip` command failed with "Operation not permitted" replacing existing zip. Fixed using Python's `zipfile` module.
4. **Apple Silicon PyAudio** — install_macos.sh handles arm64 Homebrew path (`/opt/homebrew/bin`) via `~/.zprofile`.

---

## Key Constraints & Decisions

See `DECISIONS.md` for the authoritative ADR log. Summary:
- No cross-module imports — EventBus only
- Async-first — every I/O method is `async def`
- Permission gate before every sensitive action
- 100% type hints — mypy strict mode
- Loguru lazy eval — `logger.info("msg {}", var)` not f-strings
- Python 3.11+ only — no backports

---

## File Sizes (for reference)
- `pyproject.toml`: 200 lines (full dep spec + tool config)
- `CLAUDE.md`: 615 lines (Claude Code master context)
- `docs/technology-audit.md`: ~350 lines (library decisions)
- Source code: ~6,500 LOC across 92 Python files
- Project archive: `jarvis-os-phase1-v2.zip` (116 files, 139 KB)
