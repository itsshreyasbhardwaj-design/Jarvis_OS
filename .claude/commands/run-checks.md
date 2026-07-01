# Run All Quality Checks

Run the full quality gate before committing or opening a PR.

## Execute in order:

```bash
# 1. Format (auto-fix)
ruff format src/ tests/
black src/ tests/

# 2. Lint (auto-fix safe issues)
ruff check src/ tests/ --fix

# 3. Type checking (must pass 100%)
mypy src/jarvis/ --strict

# 4. Unit tests
pytest tests/unit/ -v --tb=short

# 5. Coverage check (must be ≥70%)
pytest tests/unit/ --cov=jarvis --cov-report=term-missing --cov-fail-under=70

# 6. Security scan
bandit -r src/ -ll

# One-liner gate (CI equivalent):
make lint && make typecheck && make test
```

## If mypy fails:
- Missing type hints → add them (zero exceptions to this rule)
- `Any` types → narrow them with proper types or `cast()`
- Third-party stubs missing → add to `[[tool.mypy.overrides]]` in pyproject.toml

## If tests fail:
- Check test is using correct fixtures from `tests/conftest.py`
- Async tests need `@pytest.mark.asyncio` (or `asyncio_mode = auto` in pytest.ini)
- Mock external services — never make real API calls in unit tests
