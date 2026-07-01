# Data Flow

## Voice Command: End-to-End

This is the complete journey of a spoken command from microphone to response.

```
MICROPHONE
    │
    │ 16kHz PCM audio chunks (pyaudio)
    ▼
WakeWordDetector
    │ openwakeword model inference
    │ 2s cooldown between triggers
    │ publishes: WakeWordDetectedEvent
    ▼
AudioPipeline._record_utterance()
    │ RMS-based VAD
    │ Collects audio until 1.5s of silence
    │ Returns: np.ndarray (float32)
    ▼
SpeechTranscriber.transcribe_audio(audio_data)
    │ faster-whisper model (runs in thread pool)
    │ VAD filter, language detection
    │ Returns: TranscriptionResult(text, confidence, language)
    ▼
AudioPipeline._process_utterance(text)
    │ Publishes: UserInputEvent(text=text, source="voice")
    ▼
[via EventBus] → AI Processing Handler
    │
    ├── ContextManager.get_context()
    │       Returns: List[Message] (sliding window, within token budget)
    │
    ├── ContextManager.add_message(role=USER, content=text)
    │
    ├── AIProvider.complete(messages, tools=executor.tool_definitions)
    │       Retries: 3x with exponential backoff
    │       Returns: AIResponse(content, tool_calls, usage)
    │
    ├── [If tool_calls present]
    │   ToolExecutor.execute_all(tool_calls)
    │       For each tool:
    │           PermissionManager.check(request)
    │               ├── GRANTED → run tool function
    │               └── DENIED  → return denial message
    │       AuditLogger.log_action(...)   ← every tool call logged
    │       Returns: List[ToolResult]
    │
    ├── [If tool results] → AIProvider.complete(messages + tool_results)
    │       Returns: Final AIResponse(content)
    │
    ├── ContextManager.add_message(role=ASSISTANT, content=response)
    │
    └── Publishes: AIResponseEvent(text=response)
            │
            ▼
    TextToSpeechSynthesizer.speak(text)
            │ Coqui TTS / pyttsx3 synthesis (thread pool)
            │ sounddevice playback (async queue)
            ▼
    SPEAKERS

SIMULTANEOUSLY → UI MainWindow.add_message(role, content)
                          Adds bubble to conversation area
                          Auto-scrolls
```

---

## Text Command (UI)

When the user types instead of speaks:

```
UI Entry Widget (Enter key / Send button)
    │
    ▼
MainWindow._on_send()
    │ Publishes: UserInputEvent(text=input, source="text")
    ▼
[same AI processing path as above]
    │
    ▼
AIResponseEvent
    ├── UI: add_message(role="assistant", content)
    └── TTS: speak(content)  [only if voice_enabled]
```

---

## Tool Execution Detail

```
ToolExecutor.execute_all(tool_calls: List[ToolCall])
    │
    │ asyncio.gather(*[_execute_one(tc) for tc in tool_calls])
    │ (parallel execution where possible)
    ▼
_execute_one(tool_call: ToolCall)
    │
    ├── Look up RegisteredTool by name
    │
    ├── PermissionManager.check(PermissionRequest(
    │       action_name=tool.name,
    │       risk_level=tool.risk_level,
    │       description=tool.description,
    │       arguments=tool_call.arguments,
    │   ))
    │
    ├── [DENIED] → ToolResult(success=False, error="Permission denied")
    │
    ├── [GRANTED, requires_confirmation=True]
    │   │ confirmation_callback(request) → bool
    │   │ [User clicks No] → ToolResult(success=False, error="User declined")
    │   │ [User clicks Yes] → continue
    │
    └── asyncio.wait_for(
            tool.func(**tool_call.arguments),
            timeout=tool.timeout_seconds
        )
            ├── Success → ToolResult(success=True, content=result)
            └── Timeout → ToolResult(success=False, error="Timed out after Xs")
            └── Exception → ToolResult(success=False, error=str(e))
```

---

## Memory Read/Write

```
WRITE (after each exchange):
    ShortTermMemory.add(role, content)   ← always (fast, in-memory)
    LongTermMemory.store(content, importance=...)   ← if importance > threshold
    ConversationHistory.add_message(session_id, role, content)  ← always

READ (before each AI call):
    ContextManager.get_context()
        │
        ├── ShortTermMemory.get_recent(n)  ← recent messages always included
        │
        └── [if budget allows]
            LongTermMemory.search(recent_topic)  ← relevant past facts
```

---

## Plugin Event Flow

```
External Trigger (e.g., calendar reminder fires)
    │
    ▼
Plugin publishes: CalendarEventEvent(title, time, attendees)
    │
    ▼ [via EventBus]
    │
    ├── AI Handler (if configured to react)
    │
    └── Notification Handler
            │
            ▼
        Desktop notification + TTS announcement
