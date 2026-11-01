export PYTHONPATH := src

-include .env
export

.PHONY: install test cov lint format typecheck migration migrate db db-reset api worker openapi fe-install fe-dev fe-check fe-test fe-build

install:
	uv sync
	uv run pre-commit install

test:
	uv run pytest

cov:
	uv run pytest --cov --cov-report=term-missing

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

db:
	docker run --name localreel-db --rm -d -p $(DB_PORT):5432 \
		-e POSTGRES_USER=$(DB_USER) -e POSTGRES_PASSWORD=$(DB_PASSWORD) -e POSTGRES_DB=$(DB_NAME) \
		postgres:18-alpine

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

worker:
	uv run python -m localreel.entrypoints.worker.main

# The frontend's typed API client is generated from FastAPI's schema. Run after
# changing an endpoint or a DTO, and commit both generated files.
openapi:
	uv run python -c "import json; from localreel.entrypoints.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2))" > frontend/src/lib/api/openapi.json
	cd frontend && npm run gen:api

fe-install:
	cd frontend && npm ci

fe-dev:
	cd frontend && npm run dev

fe-check:
	cd frontend && npm run lint && npm run check

fe-test:
	cd frontend && npm test

fe-build:
	cd frontend && npm run build
