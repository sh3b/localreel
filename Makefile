export PYTHONPATH := src

.PHONY: install test lint format typecheck migration migrate db

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

db:
	docker run --name localreel-db --rm -d -p 5432:5432 \
		-e POSTGRES_USER=localreel -e POSTGRES_PASSWORD=localreel -e POSTGRES_DB=localreel \
		postgres:18-alpine

migration:  ## usage: make migration m="add videos table"
ifndef m
	$(error usage: make migration m="describe the change")
endif
	uv run alembic revision --autogenerate -m "$(m)"

migrate:
	uv run alembic upgrade head
