install:
	uv sync

dev:
	uv run python -m uvicorn app.main:app --reload --port 8000

run:
	uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

index-corpus:
	uv run python scripts/index_corpus.py

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf .venv data/app.db data/chroma __pycache__ .pytest_cache
