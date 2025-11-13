install:
	uv sync

fix: install
	uv tool run ruff check --fix .

format: install fix
	uv tool run ruff format .

lint: install
	uv tool run ruff check .
	uv tool run ruff format --check .

test: lint
	uv run pytest tests

run: install
	uv run --env-file=.env src/main.py

coverage: install pyproject.toml lint
	uv run python -m coverage run --source=src -m pytest -n 0 tests
	uv run python -m coverage html
	uv run python -m coverage lcov

clean:
	-rm -rf .venv
	-rm -rf __pycache__/
	-rm -rf src/__pycache__/
	-rm -rf tests/__pycache__/
	-rm -rf .pytest_cache/
	-rm -rf htmlcov/
	-rm -rf .coverage
	-rm -rf coverage.lcov
	-rm -rf pull_request_statistics.egg-info/
