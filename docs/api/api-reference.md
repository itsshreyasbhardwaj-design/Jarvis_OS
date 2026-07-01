# API Reference

Internal API reference for JARVIS OS modules.

---

## EventBus

```python
from jarvis.core.event_bus import EventBus, Event

bus = EventBus()
await bus.start()

# Subscribe
sub_id = bus.subscribe(
    pattern="Voice*",           # fnmatch pattern
    handler=my_async_handler,   # async def handler(event) -> None
    owner="my_module",          # for unsubscribe-by-owner
    priority=Priority.NORMAL,   # CRITICAL=0 > HIGH=1 > NORMAL=2 > LOW=3 > BACKGROUND=4
    once=False,                 # True = fire once then auto-unsubscribe
)

# Unsubscribe
bus.unsubscribe(sub_id)
bus.unsubscribe_all(owner="my_module")

# Publish
await bus.publish(MyEvent(source="my_module", data="..."))
bus.publish_sync(MyEvent(...))  # For sync contexts

# Stats
bus.stats  # dict: events_processed, errors, queue_size, subscriber_count

await bus.stop()
```

---

## AIProvider

```python
from jarvis.ai.providers.base import AIProvider, Message, Role

provider: AIProvider  # injected via ServiceRegistry

# Complete
response = await provider.complete(
    messages=[
        Message(role=Role.SYSTEM, content="..."),
        Message(role=Role.USER, content="Hello"),
    ],
    tools=[...],        # Optional: List[ToolDefinition]
    max_tokens=1024,    # Optional
    temperature=0.7,    # Optional
)
# response.content: str
# response.tool_calls: List[ToolCall]
# response.usage.total_tokens: int

# Stream
async for chunk in provider.stream(messages):
    print(chunk.content, end="", flush=True)

# Token counting
token_count = await provider.count_tokens(messages)

# Health
is_healthy = await provider.health_check()
```

---

## ToolExecutor

```python
from jarvis.ai.tool_executor import ToolExecutor
from jarvis.desktop.permissions import RiskLevel

executor = ToolExecutor(permission_manager=pm)

# Register a tool
@executor.register(
    name="read_file",
    description="Read the contents of a file",
    parameters={
        "path": {"type": "string", "description": "Absolute path to the file"},
    },
    required=["path"],
    risk_level=RiskLevel.READ_ONLY,
    requires_confirmation=False,
    timeout_seconds=10.0,
)
async def read_file(path: str) -> str:
    async with aiofiles.open(path) as f:
        return await f.read()

# Get tool definitions for AI
definitions = executor.tool_definitions  # List[ToolDefinition]

# Execute (called by AI processing loop)
results = await executor.execute_all(tool_calls)  # List[ToolResult]
```

---

## PermissionManager

```python
from jarvis.desktop.permissions import (
    PermissionManager, PermissionRequest, RiskLevel
)

pm = PermissionManager(
    require_confirmation=True,
    safe_mode=True,
    allowed_paths=["/Users/me/Documents"],
    forbidden_paths=["/System", "/etc"],
    confirmation_callback=my_async_callback,
)

# Check permission
result = await pm.check(PermissionRequest(
    action_name="delete_file",
    risk_level=RiskLevel.HIGH,
    description="Delete ~/Downloads/old.zip",
    arguments={"path": "~/Downloads/old.zip"},
))
# result.granted: bool
# result.reason: str

# Path check
allowed = pm.check_path("/Users/me/Documents/file.txt")  # bool
```

---

## LongTermMemory

```python
from jarvis.memory.long_term import LongTermMemory

mem = LongTermMemory(db_path="data/memory/long_term/memory.db")
await mem.initialize()

# Store
entry_id = await mem.store(
    content="User prefers dark mode in all applications",
    summary="Dark mode preference",
    source="conversation",      # conversation | web | file | plugin
    importance=0.8,             # 0.0–1.0
    tags=["preferences", "ui"],
    metadata={"session_id": "abc123"},
)

# Search (FTS5 full-text search)
entries = await mem.search(
    query="dark mode preferences",
    source="conversation",      # Optional filter
    min_importance=0.5,         # Optional filter
    limit=10,
)

# Recent memories
entries = await mem.get_recent(limit=20)

# Important memories
entries = await mem.get_important(min_importance=0.7, limit=10)

# Stats
stats = await mem.stats()
# {"total_entries": 142, "by_source": {...}, "avg_importance": 0.63}

await mem.close()
```

---

## KnowledgeStore (Vector Search)

```python
from jarvis.memory.knowledge_store import KnowledgeStore

store = KnowledgeStore(persist_dir="data/memory/vector_store")
await store.initialize()  # Runs in thread pool (ChromaDB init)

# Add document
entry_id = await store.add(
    content="JARVIS OS uses ChromaDB for vector storage...",
    entry_id="doc-001",          # Optional custom ID
    metadata={"source": "docs", "title": "Architecture Overview"},
)

# Semantic search
results = await store.search(
    query="how does memory work in JARVIS",
    limit=5,
    min_similarity=0.7,          # Cosine similarity threshold
)
# results: List[KnowledgeEntry] sorted by similarity desc

# Count
count = await store.count()
```

---

## JarvisPlugin

```python
from jarvis.plugins.base import JarvisPlugin, PluginMetadata, PluginContext

class Plugin(JarvisPlugin):

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="...",
            author="...",
            homepage="https://...",           # Optional
            required_permissions=["LOW"],      # Optional
            tags=["productivity"],             # Optional
            min_jarvis_version="0.1.0",       # Optional
        )

    async def start(self, context: PluginContext) -> None:
        # context.tool_executor: ToolExecutor
        # context.event_bus: EventBus
        # context.data_dir: Path  (plugin-specific data directory)
        # context.config: dict    (plugin config from settings)
        pass

    async def stop(self) -> None:
        pass

    def on_error(self, error: Exception) -> None:
        # Override to handle plugin errors
        pass
```

---

## AuditLogger

```python
from jarvis.security.audit_log import AuditLogger, AuditEntry

logger = AuditLogger(log_dir=Path("data/audit"))
await logger.initialize()

# Log an action
await logger.log_action(
    module="desktop.file_system",
    action="read_file",
    args={"path": "/Users/me/doc.txt"},
    result="success",          # success | denied | error
    risk_level=0,              # RiskLevel.READ_ONLY
    user_approved=True,
    duration_ms=12.4,
)

# Read entries (most recent first)
entries = await logger.read_entries(
    limit=100,
    module_filter="desktop",   # Optional
    result_filter="denied",    # Optional
)

logger.session_id   # Current session UUID
logger.entry_count  # Total entries written this session
```
