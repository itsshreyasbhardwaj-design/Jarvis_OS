# Coding Standards

## Python Version

**Python 3.11+** — no exceptions. We use:
- `match`/`case` statements where appropriate
- `tomllib` (stdlib)
- `asyncio.TaskGroup` for structured concurrency
- PEP 695 generics (Python 3.12+ — avoid for now)

---

## File Structure

Every Python file follows this order:

```python
"""
Module docstring — what this module does, why it exists.
"""

from __future__ import annotations  # Always first import

# Standard library
import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path

# Third-party
import numpy as np
from loguru import logger

# Internal (relative preferred within package)
from jarvis.core.event_bus import EventBus
from .base import BaseProvider

# Module-level constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0

# Classes and functions follow
```

---

## Naming Conventions

| Construct | Convention | Example |
|-----------|-----------|---------|
| Class | `PascalCase` | `SpeechTranscriber` |
| Function/method | `snake_case` | `transcribe_audio` |
| Variable | `snake_case` | `audio_data` |
| Constant | `UPPER_SNAKE` | `MAX_RETRIES` |
| Private method | `_snake_case` | `_load_model` |
| Type alias | `PascalCase` | `AudioChunk = np.ndarray` |
| Protocol | `PascalCase` | `LifecycleModule` |
| Abstract base | suffix `Base` or no suffix | `AIProvider` |
| Event | suffix `Event` | `WakeWordDetectedEvent` |
| Config class | suffix `Settings` | `AISettings` |

---

## Async Rules

**Always prefer async I/O:**

```python
# ✓ Use aiofiles for file I/O
async with aiofiles.open(path) as f:
    content = await f.read()

# ✓ Use asyncio.to_thread for blocking code
result = await asyncio.to_thread(blocking_function, arg)

# ✗ Never block the event loop
time.sleep(1)          # Use await asyncio.sleep(1)
open(path).read()      # Use aiofiles
requests.get(url)      # Use aiohttp or httpx
```

**Structured concurrency:**

```python
# ✓ Gather parallel tasks
results = await asyncio.gather(task_a(), task_b(), task_c())

# ✓ Cancel on first error
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(task_a())
    t2 = tg.create_task(task_b())
```

---

## Dataclasses vs Pydantic

| Use case | Use |
|----------|-----|
| Internal data containers | `@dataclass` |
| Config / settings | `pydantic.BaseSettings` |
| API request/response models | `pydantic.BaseModel` |
| Simple named tuples | `typing.NamedTuple` |

```python
# Internal data container
@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    duration_ms: float

# Config
class AISettings(BaseSettings):
    provider: str = "claude"
    model: str = "claude-opus-4-5"
    max_retries: int = 3
```

---

## Logging Standards

Use `loguru` exclusively. Never use `print()` in production code.

```python
from loguru import logger

# ✓ Structured, lazy-evaluated
logger.debug("Processing audio chunk: size={}, rms={:.4f}", chunk.size, rms)
logger.info("JARVIS started in {} mode", settings.environment)
logger.warning("Wake word sensitivity low: {}", sensitivity)
logger.error("API call failed after {} retries: {}", max_retries, error)
logger.critical("Cannot start: {}", reason)

# Performance logging (separate log file)
logger.bind(performance=True).info(
    "AI response: latency={}ms tokens={}", latency_ms, total_tokens
)

# ✗ Never use print
print("debug info")      # Use logger.debug
```

---

## Error Handling Hierarchy

```
JarvisError (base)
├── ConfigurationError   — bad config, missing required values
├── ProviderError        — AI provider failures
│   ├── RateLimitError
│   └── AuthenticationError
├── PermissionDeniedError — security system blocked the action
├── TimeoutError         — operation exceeded time limit
├── MemoryError          — memory subsystem failures
└── PluginError          — plugin lifecycle failures
```

Define module-specific errors in each module's `exceptions.py` (create when the module has > 2 error types).

---

## SOLID in Practice

**Single Responsibility:**
Each class does one thing. `SpeechTranscriber` transcribes. `AudioPipeline` orchestrates. They don't swap roles.

**Open/Closed:**
Add new AI providers by subclassing `AIProvider` — never modify the base or the executor.

**Liskov Substitution:**
Any `AIProvider` subclass must be swappable with any other. If your Claude-specific logic leaks into the caller, that's a violation.

**Interface Segregation:**
`LifecycleModule` is a Protocol with only what lifecycle management needs. Don't bloat it.

**Dependency Inversion:**
High-level modules (`JarvisOS`) depend on abstractions (`AIProvider`), not concretions (`ClaudeProvider`). The concrete class is selected at startup via `ServiceRegistry`.
