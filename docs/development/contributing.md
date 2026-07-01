# Contributing to JARVIS OS

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/jarvis-os.git`
3. Run setup: `bash scripts/setup.sh`
4. Create a feature branch: `git checkout -b feat/my-feature`

---

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready, always deployable |
| `develop` | Integration branch for features |
| `feat/*` | New features |
| `fix/*` | Bug fixes |
| `refactor/*` | Refactoring (no functional change) |
| `docs/*` | Documentation only |
| `chore/*` | Tooling, deps, CI changes |

**Never commit directly to `main`.**

---

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer: closes #123]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, `revert`

Examples:
```
feat(ai): add Gemini provider with streaming support
fix(voice): correct RMS threshold causing early cutoff
docs(plugins): add plugin development guide
test(memory): add FTS5 search coverage for LongTermMemory
chore(deps): upgrade anthropic to 0.25.0
```

Pre-commit hooks enforce this format automatically.

---

## Code Standards

### Type Hints — Always

```python
# ✓ Good
async def transcribe_audio(self, audio_data: np.ndarray) -> TranscriptionResult:

# ✗ Bad
async def transcribe_audio(self, audio_data):
```

### Docstrings — Public APIs

```python
def store(
    self,
    content: str,
    importance: float = 0.5,
) -> str:
    """
    Store a memory entry in long-term storage.

    Args:
        content: The text to store.
        importance: Score from 0.0 to 1.0. High-importance
                    entries are retrieved preferentially.

    Returns:
        The entry_id of the stored memory.

    Raises:
        DatabaseError: If the write fails.
    """
```

### Error Handling — No Silent Failures

```python
# ✓ Good
try:
    result = await self._call_api()
except APIConnectionError as e:
    logger.error("API call failed: {}", e)
    raise  # or return a typed error result

# ✗ Bad
try:
    result = await self._call_api()
except Exception:
    pass  # Never do this
```

### No Direct Cross-Module Imports

```python
# ✓ Good — communicate through EventBus
await self._bus.publish(VoiceCommandEvent(text=text))

# ✗ Bad — direct coupling between modules
from jarvis.ai.processor import process_command
await process_command(text)
```

---

## Testing Requirements

All new code must include tests:

| Code Type | Required Tests |
|-----------|---------------|
| New module | At least 3 unit tests for public methods |
| Bug fix | Regression test that would have caught the bug |
| New tool | Permission level test + success path test |
| New plugin | Start/stop lifecycle test + tool registration test |

Run tests before pushing:
```bash
make test-unit
make lint
make type-check
```

---

## Pull Request Checklist

- [ ] Branch is from `develop`, not `main`
- [ ] Commit messages follow Conventional Commits
- [ ] All tests pass (`make test`)
- [ ] No new linter errors (`make lint`)
- [ ] Type checks pass (`make type-check`)
- [ ] New code has docstrings on public APIs
- [ ] New features have corresponding tests
- [ ] `ROADMAP.md` updated if applicable
- [ ] PR description explains *why*, not just *what*

---

## Module Placement Guide

| What you're adding | Where it goes |
|---------------------|--------------|
| New AI provider | `src/jarvis/ai/providers/` |
| New voice component | `src/jarvis/voice/` |
| New memory backend | `src/jarvis/memory/` |
| New desktop capability | `src/jarvis/desktop/` |
| New browser capability | `src/jarvis/browser/` |
| New plugin | `src/jarvis/plugins/examples/` (built-in) or `~/.jarvis/plugins/` (user) |
| New UI component | `src/jarvis/ui/` |
| New config option | `src/jarvis/config/settings.py` + `.env.example` |
| New event type | Module's own file, e.g. `src/jarvis/voice/events.py` |
