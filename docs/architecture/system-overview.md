# JARVIS OS — System Architecture Overview

## Design Philosophy

JARVIS OS is built on five core architectural principles:

1. **Event-Driven**: All inter-module communication flows through a typed async event bus
2. **Dependency Injection**: Services are resolved through a central registry, never imported directly
3. **Permission-Gated**: Every action above READ_ONLY requires explicit approval at the permission layer
4. **Provider-Agnostic**: AI providers, TTS engines, and storage backends are swappable via config
5. **Fail-Safe**: Safe mode blocks all HIGH+ risk actions; no silent failures

---

## System Layers

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface (UI)                   │
│             CustomTkinter dark-theme window              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Core Application                       │
│      JarvisOS → LifecycleManager → EventBus             │
│                 ServiceRegistry                          │
└──┬──────────┬──────────┬──────────┬────────────────┬────┘
   │          │          │          │                │
┌──▼──┐  ┌───▼──┐  ┌────▼───┐  ┌──▼──────┐  ┌────▼────┐
│ AI  │  │Voice │  │Memory  │  │Desktop  │  │Browser  │
│Layer│  │Layer │  │Layer   │  │Layer    │  │Layer    │
└──┬──┘  └───┬──┘  └────┬───┘  └──┬──────┘  └────┬────┘
   │          │          │         │               │
┌──▼──────────▼──────────▼─────────▼───────────────▼────┐
│                   Security Layer                        │
│        PermissionManager + AuditLogger                 │
└─────────────────────────────────────────────────────────┘
```

---

## Core Module: Event Bus

The `EventBus` is the nervous system of JARVIS OS. All cross-module communication is asynchronous and mediated through typed events.

```python
# Publishing
await bus.publish(VoiceCommandEvent(text="Open Chrome"))

# Subscribing
bus.subscribe("VoiceCommand*", handle_voice, owner="ai_layer")
```

Key properties:
- Priority queue (CRITICAL → HIGH → NORMAL → LOW → BACKGROUND)
- Pattern-based subscriptions (fnmatch: `Voice*`, `*Error*`, `SystemShutdown`)
- Dead letter queue for unhandled events
- Per-handler error isolation (one crash doesn't stop others)

---

## AI Layer

```
User Input
    │
    ▼
ContextManager (sliding window, token budget)
    │
    ▼
AIProvider.complete(messages, tools)
    │        ├── ClaudeProvider
    │        ├── OpenAIProvider
    │        ├── GeminiProvider
    │        └── LocalProvider (llama.cpp)
    │
    ▼ (if tool calls present)
ToolExecutor.execute_all(tool_calls)
    │
    ▼
Final Response
```

**Provider Selection**: Set `JARVIS_AI_PROVIDER=claude|openai|gemini|local` in `.env`. No code changes required.

---

## Voice Pipeline

```
Microphone
    │
    ▼
WakeWordDetector (openwakeword — "hey jarvis")
    │  cooldown: 2s between detections
    ▼
AudioPipeline._record_utterance()
    │  RMS VAD, 1.5s silence = end of utterance
    ▼
SpeechTranscriber (faster-whisper)
    │  base.en model, VAD filter
    ▼
AI Processing
    │
    ▼
TextToSpeechSynthesizer (Coqui TTS / pyttsx3)
    │
    ▼
Speakers
```

---

## Memory Architecture

| Store | Backend | Use Case |
|-------|---------|----------|
| ShortTermMemory | Python deque | Recent conversation (last N messages) |
| LongTermMemory | SQLite + FTS5 | Searchable facts, task history |
| KnowledgeStore | ChromaDB | Semantic/vector search over documents |
| ConversationHistory | SQLite | Full session history |
| UserPreferences | JSON file | Settings (UI theme, language, etc.) |

---

## Plugin Framework

```python
class Plugin(JarvisPlugin):
    # 1. Declare metadata (name, version, permissions required)
    # 2. Register tools in start(context)
    # 3. Tools execute with permission checks
    # 4. Clean up in stop()
```

Plugins are loaded from `~/.jarvis/plugins/` at startup. Each plugin runs in an isolated error boundary — a crash in one plugin does not affect others.

---

## Security Model

See [Security Model](../security/security-model.md) for full details.

**Risk Level Matrix:**

| Level | Examples | Default Behavior |
|-------|----------|-----------------|
| READ_ONLY | List files, take screenshot | Always allowed |
| LOW | Open app, search web | Always allowed |
| MEDIUM | Type text, click buttons | Requires confirmation |
| HIGH | Delete files, run commands | Blocked in safe_mode |
| CRITICAL | System changes, format disk | Always blocked in safe_mode |
