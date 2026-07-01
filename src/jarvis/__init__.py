"""
JARVIS OS — AI Personal Desktop Assistant
==========================================

A production-grade, modular AI desktop assistant built on clean architecture
principles. JARVIS is designed to be voice-controlled, context-aware, and
capable of autonomous multi-step task execution with user approval gates.

Architecture Overview:
  - core/         → Event bus, DI container, lifecycle management
  - ai/           → Provider abstraction, context, tool execution
  - voice/        → Wake word, STT, TTS, audio pipeline
  - memory/       → Short/long-term memory, vector store, preferences
  - desktop/      → File system, keyboard/mouse, window management
  - browser/      → Web automation via Playwright
  - security/     → Permissions, audit logs, credential storage
  - plugins/      → Extensible plugin framework
  - ui/           → Desktop UI with design system
  - config/       → Centralized configuration (Pydantic)
  - services/     → Scheduler, notifications
  - logging/      → Structured logging with Loguru

Usage:
    from jarvis import JarvisOS
    app = JarvisOS()
    app.run()
"""

from importlib.metadata import PackageNotFoundError, version

__author__ = "Shrey"
__email__ = "shreyas.b.hlc0004@gmail.com"
__license__ = "MIT"

try:
    __version__ = version("jarvis-os")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"

__all__ = ["__version__", "__author__"]
