# === Makefile for canon ===

.PHONY: help install lint format type-check test check clean build pre-commit

# Default target
help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies with uv"
	@echo "  make lint        - Run ruff linter"
	@echo "  make format      - Run ruff formatter"
	@echo "  make type-check  - Run mypy type checker"
	@echo "  make test        - Run pytest"
	@echo "  make check       - Run all checks (lint + type-check + test)"
	@echo "  make build       - Build package with uv"
	@echo "  make pre-commit  - Install and run pre-commit hooks"
	@echo "  make clean       - Remove cache and build artifacts"

# Install dependencies
install:
	uv sync --all-extras

# Linting with ruff
lint:
	uv run ruff check src tests

# Format code with ruff
format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

# Type checking with mypy
type-check:
	uv run mypy src

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=src/mcp_canon --cov-report=term-missing

# Run all checks (without formatting)
check: lint type-check test

# Clean up cache files
clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build package
build:
	uv build

# Install pre-commit hooks
pre-commit:
	uv run pre-commit install
	uv run pre-commit run --all-files

