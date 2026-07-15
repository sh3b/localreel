export PYTHONPATH := src

.PHONY: install test lint format typecheck

install:
	uv sync
	uv run pre-commit install

test:
	uv run pytest

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests
