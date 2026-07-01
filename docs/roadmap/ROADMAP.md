# JARVIS OS — Roadmap

## Phase 1: Foundation (Current)

**Status: In Progress**

The production-grade architecture and all base infrastructure.

- [x] Event bus (async, priority, dead letter queue)
- [x] Dependency injection container
- [x] Lifecycle management with health checks
- [x] AI provider abstraction (Claude, OpenAI, Gemini, Local)
- [x] Context window management with sliding window
- [x] Tool execution engine with permission gating
- [x] Wake word detection (openwakeword)
- [x] Speech-to-text (faster-whisper)
- [x] Text-to-speech (Coqui TTS / pyttsx3)
- [x] Audio pipeline with VAD
- [x] Short-term memory (deque)
- [x] Long-term memory (SQLite + FTS5)
- [x] Vector knowledge store (ChromaDB)
- [x] Conversation history
- [x] User preferences
- [x] File system navigation + permissions
- [x] Keyboard + mouse automation
- [x] Screen capture + OCR
- [x] Application launcher
- [x] Browser automation (Playwright)
- [x] Permission system with risk levels
- [x] Append-only audit log
- [x] OS keychain credential storage
- [x] Plugin framework
- [x] Dark theme UI (CustomTkinter)
- [x] Loguru structured logging
- [x] Pytest test suite + CI

---

## Phase 2: Feature Depth

**Target: 3-4 months after Phase 1**

- [ ] Calendar integration (Google Calendar / Apple Calendar)
- [ ] Email reading + drafting
- [ ] Web research agent (multi-page summarization)
- [ ] Code execution sandbox (Docker-based)
- [ ] File summarization and Q&A
- [ ] Desktop notification center
- [ ] Clipboard manager
- [ ] Window management (resize, move, focus)
- [ ] Multi-monitor support
- [ ] Hotkey customization
- [ ] Plugin marketplace (discovery + install via CLI)

---

## Phase 3: Intelligence

**Target: 6-8 months after Phase 1**

- [ ] Long-running task execution with checkpoints
- [ ] User preference learning (auto-adapts to habits)
- [ ] Multi-agent coordination (specialized sub-agents)
- [ ] Proactive suggestions (not just reactive)
- [ ] Scheduled tasks (cron-like with AI trigger conditions)
- [ ] Cross-device sync (mobile companion app)
- [ ] Improved wake word with custom model training
- [ ] Streaming voice responses (lower latency)

---

## Phase 4: Distribution

**Target: 12+ months**

- [ ] macOS app bundle (.app + Sparkle auto-update)
- [ ] Windows installer
- [ ] Linux AppImage
- [ ] Plugin SDK (separate package)
- [ ] Developer documentation site
- [ ] End-user documentation site
- [ ] Community plugin repository
