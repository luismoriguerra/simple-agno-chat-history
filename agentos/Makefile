PYTHON = uv run python

sync:
	uv sync
	source .venv/bin/activate

dev:
	uv run fastapi dev src/main.py

test:
	$(PYTHON) -m pytest tests/ -v -m agent_test