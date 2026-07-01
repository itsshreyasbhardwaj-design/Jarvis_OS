# Phase 2 Feature Implementation Plan

Phase 1 (foundation) is complete. This command gives context for starting Phase 2.

## Before starting ANY Phase 2 feature, read:
1. `CLAUDE.md` — architecture rules and patterns
2. `docs/architecture/data-flow.md` — how events flow through the system
3. `docs/roadmap/ROADMAP.md` — full Phase 2 scope

## Phase 2 Feature: $ARGUMENTS

### Implementation pattern for all Phase 2 features:

1. **Create module** `src/jarvis/$ARGUMENTS/`
2. **Define events** the module publishes and consumes
3. **Register lifecycle** in orchestrator at priority 30-39
4. **Add tools** via `@tool_executor.register()`
5. **Subscribe to voice events** to handle natural language triggers
6. **Write tests** in `tests/unit/test_$ARGUMENTS/`
7. **Document** in `docs/` and update `docs/roadmap/ROADMAP.md`

### Example: Adding calendar integration
```python
# src/jarvis/calendar/manager.py
class CalendarManager:
    async def start(self) -> None:
        await self._event_bus.subscribe(
            "jarvis.voice.transcription_complete",
            self._handle_voice_input,
        )
        # Register tools
        self._tool_executor.register_many([
            self._get_upcoming_events,
            self._create_event,
            self._find_free_time,
        ])

    async def _handle_voice_input(self, event: Event) -> None:
        text = event.data["text"].lower()
        if any(kw in text for kw in ["calendar", "schedule", "meeting", "event"]):
            await self._event_bus.publish(
                "jarvis.calendar.intent_detected",
                data={"text": event.data["text"]},
            )
```

### Key Phase 2 priorities (in order):
1. Web research (search + summarize) — highest utility
2. Email (read + draft) — daily use case
3. File management — voice-controlled finder
4. Calendar — scheduling via voice
5. Code execution — sandboxed Python runner
6. System monitoring — CPU/RAM/disk on demand
