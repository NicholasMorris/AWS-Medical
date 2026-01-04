PY=python -m

.PHONY: test coverage run-visualizer run-webapp run-pipeline install-dev format lint

test:
	# Run tests
	pytest -q

coverage:
	pytest --cov=src --cov-report=term

run-visualizer:
	# Start the Shiny visualizer (auto-reloads)
	python -m shiny run webapp.app:app --reload --port 8002

run-webapp: run-visualizer

run-pipeline:
	# Helper to run the end-to-end local pipeline
	python scripts/run_pipeline.py

install-dev:
	# Install editable package and dev requirements
	uv pip install -e .
	pip install -r requirements-dev.txt || true

format:
	black .

lint:
	pylint src || true
env:
	uv pip install -e .