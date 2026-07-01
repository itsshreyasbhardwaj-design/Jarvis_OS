# ==============================================================================
# JARVIS OS — Makefile
# All development commands in one place.
# Usage: make <target>
# ==============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash
PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
BLACK := $(VENV)/bin/black

.PHONY: help install install-dev setup clean lint format type-check test test-unit \
        test-integration test-cov run dev docs check pre-commit update-deps \
        playwright-install jarvis

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help: ## Show this help message
	@echo "JARVIS OS — Development Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup & Installation
# ---------------------------------------------------------------------------
$(VENV)/bin/activate: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

setup: $(VENV)/bin/activate ## Create venv and install all dependencies
	@echo "✓ Virtual environment ready"
	$(VENV)/bin/pre-commit install --install-hooks
	$(VENV)/bin/pre-commit install --hook-type commit-msg
	@echo "✓ Pre-commit hooks installed"
	cp -n .env.example .env || true
	@echo "✓ .env created from .env.example (edit it!)"
	@mkdir -p data/{logs,memory/{short_term,long_term,vector_store},models,audit,plugins}
	@echo "✓ Data directories created"

install: ## Install production dependencies only
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

install-dev: ## Install all dependencies including dev tools
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"

playwright-install: ## Install Playwright browsers
	$(VENV)/bin/playwright install chromium firefox webkit

update-deps: ## Upgrade all dependencies to latest compatible versions
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -e ".[dev]"

# ---------------------------------------------------------------------------
# Code Quality
# ---------------------------------------------------------------------------
lint: ## Run ruff linter
	$(RUFF) check src/ tests/

lint-fix: ## Run ruff linter and auto-fix issues
	$(RUFF) check --fix src/ tests/

format: ## Format code with ruff + black
	$(RUFF) format src/ tests/
	$(BLACK) src/ tests/

format-check: ## Check formatting without modifying files
	$(RUFF) format --check src/ tests/
	$(BLACK) --check src/ tests/

type-check: ## Run mypy type checker
	$(MYPY) src/jarvis --config-file pyproject.toml

check: lint format-check type-check ## Run all quality checks (no modifications)

pre-commit: ## Run all pre-commit hooks on all files
	$(VENV)/bin/pre-commit run --all-files

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test: ## Run all tests
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	$(PYTEST) tests/integration/ -v -m integration

test-fast: ## Run tests excluding slow ones
	$(PYTEST) tests/ -v -m "not slow" --tb=short

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=jarvis --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode (requires pytest-watch)
	$(VENV)/bin/ptw tests/ src/ -- -x --tb=short

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
run: ## Start JARVIS OS
	$(VENV)/bin/jarvis

dev: ## Start JARVIS OS in development mode (verbose logging)
	JARVIS_ENV=development JARVIS_LOG_LEVEL=DEBUG $(VENV)/bin/jarvis

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------
docs: ## Build and serve documentation locally
	@echo "Open docs/architecture/README.md to get started"
	@echo "Full docs: docs/"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove all build artifacts, caches, and temporary files
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage .coverage.*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Cleaned"

clean-all: clean ## Remove everything including the virtual environment
	rm -rf $(VENV)
	@echo "✓ Virtual environment removed"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
.SECRETS_BASELINE := .secrets.baseline
secrets-baseline: ## Generate detect-secrets baseline
	$(VENV)/bin/detect-secrets scan > $(SECRETS_BASELINE)

loc: ## Count lines of code
	@find src/ -name "*.py" | xargs wc -l | tail -1

deps-tree: ## Show dependency tree
	$(PIP) install pipdeptree 2>/dev/null; $(VENV)/bin/pipdeptree

verify: ## Verify the full project setup is correct
	@echo "Verifying JARVIS OS setup..."
	@$(PYTHON) -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
	@echo "✓ Python version OK"
	@$(VENV)/bin/python -c "import jarvis; print('✓ Package imports OK')"
	@echo "All checks passed!"
