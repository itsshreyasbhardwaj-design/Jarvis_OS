# JARVIS OS — Security Model

## Core Principle

**Never take an irreversible action without explicit user confirmation.**

JARVIS operates on a zero-trust model for sensitive operations. Even when a command is clearly intentional, destructive actions (delete, format, send, run) require real-time user approval.

---

## Risk Levels

```python
class RiskLevel(IntEnum):
    READ_ONLY = 0   # List files, read content, take screenshots
    LOW       = 1   # Open applications, navigate browser, search
    MEDIUM    = 2   # Type text, click buttons, create files
    HIGH      = 3   # Delete files, run shell commands, send emails
    CRITICAL  = 4   # Format disk, system configuration changes
```

### Safe Mode (Default: ON)

When `JARVIS_SAFE_MODE=true`:
- `READ_ONLY` + `LOW`: Auto-allowed, no prompt
- `MEDIUM`: Requires user confirmation
- `HIGH` + `CRITICAL`: **Blocked entirely**

When `JARVIS_SAFE_MODE=false`:
- All levels require confirmation except READ_ONLY + LOW
- HIGH requires confirmation (not blocked)
- CRITICAL still requires confirmation + additional warning

---

## Permission Flow

```
Action Request
      │
      ▼
PermissionManager.check(request)
      │
      ├── RiskLevel.READ_ONLY → ✓ Granted immediately
      │
      ├── RiskLevel.LOW → ✓ Granted immediately
      │
      ├── RiskLevel.MEDIUM → Ask user → ✓/✗
      │
      ├── RiskLevel.HIGH → safe_mode? Block : Ask user → ✓/✗
      │
      └── RiskLevel.CRITICAL → safe_mode? Block : Ask user + warn → ✓/✗
```

---

## Forbidden Paths

The following paths can never be accessed regardless of permission level or safe mode setting:

```python
DEFAULT_FORBIDDEN_PATHS = [
    "/System", "/Library", "/usr", "/etc",
    "/bin", "/sbin", "/private",
    "C:\\Windows", "C:\\Program Files",
]
```

---

## Audit Log

Every action — approved or denied — is written to an append-only JSONL file at `data/audit/jarvis-audit.jsonl`.

Each entry contains:
- Timestamp + session ID
- Module + action name
- Arguments (sanitized — no credential values)
- Result (success/denied/error)
- Risk level
- Whether user approved
- Duration in milliseconds

**The audit log is append-only.** It is never overwritten, only rotated.

---

## Credential Storage

API keys and passwords are stored in the OS keychain (macOS Keychain, Linux Secret Service, Windows Credential Locker) via the `keyring` library.

**Never store credentials in:**
- `.env` files (for production)
- Logs
- Database
- Memory dumps

Development exception: `.env` is acceptable during local development. Never commit `.env`.

---

## Plugin Security

Plugins execute in an isolated error boundary but **share the same process**. Plugin sandboxing is a roadmap item.

Until sandboxing is implemented:
- Only install plugins from trusted sources
- Review plugin code before installation
- Plugins inherit all permission gates
- Plugin crashes are caught and logged, not propagated
