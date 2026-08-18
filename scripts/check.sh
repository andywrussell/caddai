#!/usr/bin/env bash
# Run the full local quality gate: format check, lint, type check, tests.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> uv sync --frozen"
uv sync --frozen

echo "==> ruff format --check ."
uv run ruff format --check .

echo "==> ruff check ."
uv run ruff check .

echo "==> mypy src"
uv run mypy src

echo "==> pytest"
uv run pytest

echo "All quality gates passed."
