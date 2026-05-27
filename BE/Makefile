install:
	uv sync

dev:
	uv run python -m uvicorn app.main:app --reload --port 8000

run:
	uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

test-rag:
	uv run python scripts/test_llamacloud_rag.py

pipeline-status:
	uv run python scripts/llamacloud_pipeline_status.py

repair-pipeline:
	uv run python scripts/repair_llamacloud_pipeline.py

build-rag-bundles:
	uv run python scripts/build_llamacloud_bundles.py

ingest-rag-bundles:
	uv run python scripts/ingest_llamacloud_bundles.py

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf .venv data/app.db __pycache__ .pytest_cache
