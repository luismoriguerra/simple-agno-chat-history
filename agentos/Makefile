PYTHON = uv run python

sync:
	uv sync
	source .venv/bin/activate

dev:
	uv run fastapi dev src/main.py

test:
	$(PYTHON) -m pytest tests/ -v -m agent_test

test-unit:
	$(PYTHON) -m pytest tests/test_state_model.py tests/test_control_flow.py -v
