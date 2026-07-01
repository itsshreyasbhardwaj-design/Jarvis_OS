# JARVIS OS — Architecture Decision Log

Quick reference for WHY each major choice was made. Read this before changing anything.

## ADR-001: Event-Driven Architecture (EventBus)
**Decision:** All inter-module communication via async EventBus (no direct imports)  
**Why:** Enables zero-coupling between modules, plug-in-play for plugins, testability  
**Consequence:** Slightly more verbose than direct calls; tradeoff is worth it

## ADR-002: Dependency Injection (ServiceRegistry)
**Decision:** All services registered/resolved via ServiceRegistry, never instantiated directly  
**Why:** Enables mock injection in tests, clean lifecycle ordering, circular dep detection  
**Pattern:** `registry.get(LongTermMemory)` not `LongTermMemory()`

## ADR-003: Permission Gate on All Sensitive Operations
**Decision:** Every action with RiskLevel > READ_ONLY must call `permissions.check()` first  
**Why:** JARVIS touches keyboard, screen, files — must be safe by default  
**Pattern:** Check BEFORE the action, not after

## ADR-004: RealtimeSTT over faster-whisper standalone
**Decision:** `RealtimeSTT` wrapping whisper.cpp backend, not `faster-whisper` directly  
**Why:** faster-whisper has no Metal GPU support on macOS (CPU-only, 3-5x slower)  
**Verified:** June 2026 GitHub research, 9.8k stars, actively maintained

## ADR-005: sherpa-onnx over openwakeword
**Decision:** `sherpa-onnx` for wake word detection  
**Why:** openwakeword pre-trained models are CC BY-NC-SA (non-commercial license only)  
**Verified:** June 2026, 13.1k stars, Apache-2.0 full stack, CoreML on Apple Silicon

## ADR-006: kokoro + RealtimeTTS over Coqui TTS
**Decision:** `RealtimeTTS` engine layer + `kokoro` model  
**Why:** coqui-ai/TTS repo is officially ARCHIVED since January 2024 (unmaintained)  
**Quality:** kokoro = 9/10 quality, ~150ms latency, Apache-2.0, runs on Apple MPS

## ADR-007: lancedb over chromadb
**Decision:** `lancedb` for vector storage  
**Why:** Rust-backed HNSW, hybrid vector+FTS in one query, no server, persistent by default  
**Benchmark:** ~40% faster search than ChromaDB on 10k+ document collections

## ADR-008: PySide6 over customtkinter
**Decision:** `PySide6` (Qt6) + `pyqtgraph` for UI  
**Why:** customtkinter is Tk-based, cannot do 60fps GPU-rendered voice waveform animations  
**Qt6 wins:** Native macOS dark mode, QPropertyAnimation, pyqtgraph OpenGL, qasync for asyncio

## ADR-009: atomacos + pynput over pyautogui
**Decision:** `atomacos` (AX Accessibility API) + `pynput` (CGEvent)  
**Why:** pyautogui generates synthetic events that many native macOS apps ignore (508 open issues)  
**Reliability:** atomacos clicks by AX role/label — works on all macOS native apps

## ADR-010: Apple Vision (pyobjc) over pytesseract
**Decision:** `pyobjc-framework-Vision` for OCR, not Tesseract  
**Why:** Built-in to macOS, Neural Engine speed, zero download, same engine as iOS Live Text  
**Accuracy:** Dramatically better than Tesseract 5 on typical UI screenshots

## ADR-011: litellm as LLM router
**Decision:** Route all LLM calls through `litellm` first  
**Why:** Enables swapping Claude/GPT/local model via `.env` change, no code modification  
**Override:** Direct `anthropic` SDK still used for Claude-specific features (extended thinking)

## ADR-012: fastembed over sentence-transformers as default
**Decision:** `fastembed` as default embeddings, `sentence-transformers` as optional  
**Why:** ONNX, 80 MB RAM (vs 200 MB), no PyTorch dep, faster cold start  
**Trade-off:** No MPS acceleration (ONNX CPU runtime faster than PyTorch for small batches anyway)

## ADR-013: typer over click
**Decision:** `typer` for all CLI commands  
**Why:** typer vendors click internally; same ecosystem + type-hint native + better DX  
**Migration:** Zero code changes needed — all click commands work unchanged via typer

## ADR-014: Loguru over stdlib logging
**Decision:** `loguru` throughout, not `logging` module  
**Why:** Zero config, lazy evaluation (pass args not f-strings), `enqueue=True` for thread safety  
**Rule:** Always `logger.info("msg {}", var)` NOT `logger.info(f"msg {var}")`

## ADR-015: Python 3.11+ minimum
**Decision:** Requires Python 3.11+, no backport support  
**Why:** `asyncio.TaskGroup`, `tomllib` in stdlib, `ExceptionGroup`, faster CPython  
**Impact:** Not available on older macOS (pre-Monterey) — document this requirement
