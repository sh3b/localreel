export PYTHONPATH := src

-include .env
export

.PHONY: install test cov check format typecheck migration migrate db db-reset db-logs

install:
	uv sync
	uv run pre-commit install

test:
	uv run pytest

cov:
	uv run pytest --cov --cov-report=term-missing


check: format typecheck

typecheck:
	uv run mypy

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

db:
	docker compose up -d db

db-logs:
	docker compose logs -f db

db-reset:
	docker exec localreel-db dropdb -U $(DB_USER) --if-exists --force $(DB_NAME)
	docker exec localreel-db createdb -U $(DB_USER) $(DB_NAME)
	$(MAKE) migrate

migration:  ## usage: make migration m="add videos table"
ifndef m
	$(error usage: make migration m="describe the change")
endif
	uv run alembic revision --autogenerate -m "$(m)"

migrate:
	uv run alembic upgrade head

api:
	uv run uvicorn localreel.entrypoints.api.main:create_app --factory --reload
