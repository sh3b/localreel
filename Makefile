export PYTHONPATH := src

.PHONY: test

test:
	uv run pytest
