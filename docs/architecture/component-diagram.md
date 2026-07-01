# Component Diagram

## Top-Level Component Map

```
┌──────────────────────────────────────────────────────────────────┐
│                        JARVIS OS Process                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    JarvisOS (application.py)            │    │
│  │   LifecycleManager ←→ ServiceRegistry ←→ EventBus      │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │ orchestrates                       │
│         ┌───────────────────┼──────────────────────┐            │
│         │                   │                      │            │
│  ┌──────▼──────┐   ┌────────▼────────┐   ┌────────▼─────────┐  │
│  │  AI Layer   │   │  Voice Layer    │   │  Memory Layer    │  │
│  │             │   │                 │   │                  │  │
│  │ AIProvider  │   │ WakeWordDet.    │   │ ShortTermMemory  │  │
│  │ (abstract)  │   │ SpeechTranscr.  │   │ LongTermMemory   │  │
│  │ ┌─────────┐ │   │ TTSSynthesizer  │   │ KnowledgeStore   │  │
│  │ │ Claude  │ │   │ AudioPipeline   │   │ ConvHistory      │  │
│  │ │ OpenAI  │ │   └────────┬────────┘   │ UserPreferences  │  │
│  │ │ Gemini  │ │            │            └──────────────────┘  │
│  │ │ Local   │ │            │ events                           │
│  │ └─────────┘ │            ▼                                  │
│  │ ContextMgr  │   ┌─────────────────┐                        │
│  │ ToolExecutor│   │   EventBus      │◄────────────────────┐  │
│  └─────────────┘   │  (event_bus.py) │                     │  │
│                    └────────┬────────┘                     │  │
│         ┌──────────────────┬┘                              │  │
│         │                  │                               │  │
│  ┌──────▼──────┐   ┌───────▼──────────┐   ┌──────────────▼┐ │
│  │ Desktop     │   │ Browser Layer    │   │ Security      │ │
│  │ Layer       │   │                  │   │ Layer         │ │
│  │             │   │ BrowserManager   │   │               │ │
│  │ FileNav     │   │ WebSearcher      │   │ PermissionMgr │ │
│  │ Keyboard    │   │ ContentExtractor │   │ AuditLogger   │ │
│  │ Mouse       │   └──────────────────┘   │ CredentialStr │ │
│  │ ScreenCapt  │                          └───────────────┘ │
│  │ AppLauncher │                                             │
│  └─────────────┘                                             │
│                                                              │
│  ┌─────────────┐   ┌──────────────────┐   ┌──────────────┐ │
│  │  Plugin     │   │  Config          │   │   UI Layer   │ │
│  │  Framework  │   │  Layer           │   │              │ │
│  │             │   │                  │   │ MainWindow   │ │
│  │ PluginReg.  │   │ Settings         │   │ DesignSystem │ │
│  │ JarvisPlugin│   │ (Pydantic v2)    │   │ Colors       │ │
│  │ PluginCtx   │   │ .env / envvars   │   │ Typography   │ │
│  └─────────────┘   └──────────────────┘   └──────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Dependency Rules (Enforced by Architecture)

```
                    ┌─────────────┐
                    │   Config    │   ← No dependencies (leaf node)
                    └──────┬──────┘
                           │ read by
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌──────────┐  ┌────────┐
         │Security│  │  Core    │  │Logging │  ← Depend only on Config
         └───┬────┘  └────┬─────┘  └────────┘
             │            │ provides
             │    ┌───────┴────────┐
             │    ▼                ▼
             │  EventBus    ServiceRegistry    ← Core primitives
             │    │
             └────┤ injects into
                  ▼
         ┌────────────────────────────────┐
         │  AI / Voice / Memory / Desktop │  ← Feature modules
         │  Browser / Plugins / UI        │    (never import each other directly)
         └────────────────────────────────┘
```

### Key Rules

1. Feature modules **never import each other directly** — they communicate through the EventBus
2. All feature modules depend on **Config** and **Core** — nothing else
3. Security is a **cross-cutting concern** injected into every action that needs it
4. The UI only subscribes to events — it never calls feature modules directly
5. Plugins are **fully isolated** — they only interact through `PluginContext`

---

## Module Startup Order

```
Priority 0-9:   Config → Logging → EventBus → ServiceRegistry
Priority 10-19: Security (AuditLogger, CredentialStore, PermissionManager)
Priority 20-29: Memory (ShortTerm, LongTerm, KnowledgeStore, Preferences)
Priority 30-39: AI (provider init, tool executor)
Priority 40-49: Voice (wake word, STT, TTS)
Priority 50-59: Desktop + Browser
Priority 60-69: Plugins (alphabetical within tier)
Priority 70-79: UI
Priority 80+:   Background workers, health check loop
```

Shutdown proceeds in reverse order.
