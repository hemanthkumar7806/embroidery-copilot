#!/usr/bin/env python3
"""Delete failed pipeline (frees file quota) and create a fresh index with small ingest.

Free tier limits:
  - 50 files per organization (your failed run hit 52)
  - Gemini embed ~100 requests/minute

Usage:
  uv run python scripts/reset_llamacloud_pipeline.py
  uv run python scripts/reset_llamacloud_pipeline.py --keep-pipeline-id ecc9c499-...
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from llama_cloud import LlamaCloud

from app.core.config import settings

# Reuse create script helpers
from create_llamacloud_pipeline import (  # noqa: E402
    DEFAULT_PIPELINE_NAME,
    _embedding_config,
    _ingest_markdown,
    _wait_for_index,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset LlamaCloud pipeline and re-ingest")
    parser.add_argument(
        "--delete-id",
        default=settings.LLAMA_CLOUD_PIPELINE_ID,
        help="Pipeline to delete first (frees org file quota)",
    )
    parser.add_argument("--name", default=DEFAULT_PIPELINE_NAME)
    parser.add_argument("--max-files", type=int, default=8, help="Stay well under 50 org limit")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--batch-delay", type=int, default=120)
    parser.add_argument("--skip-delete", action="store_true")
    args = parser.parse_args()

    if not settings.LLAMA_CLOUD_API_KEY or not settings.LLAMA_CLOUD_PROJECT_ID:
        raise SystemExit("Set LLAMA_CLOUD_API_KEY and LLAMA_CLOUD_PROJECT_ID in BE/.env")

    client = LlamaCloud(api_key=settings.LLAMA_CLOUD_API_KEY)

    if args.delete_id and not args.skip_delete:
        print(f"Deleting pipeline {args.delete_id} (clears stuck files)...")
        try:
            client.pipelines.delete(pipeline_id=args.delete_id)
            print("Deleted.")
        except Exception as exc:
            print(f"Delete warning: {exc}")
        time.sleep(5)

    print(f"Creating pipeline '{args.name}'...")
    pipeline = client.pipelines.upsert(
        name=args.name,
        project_id=settings.LLAMA_CLOUD_PROJECT_ID,
        pipeline_type="MANAGED",
        embedding_config=_embedding_config(),
        llama_parse_parameters={"tier": "fast", "version": "latest"},
        transform_config={"mode": "auto", "chunk_size": 1024, "chunk_overlap": 128},
    )
    pipeline_id = pipeline.id
    print()
    print("=" * 60)
    print("Update BE/.env:")
    print(f"LLAMA_CLOUD_PIPELINE_ID={pipeline_id}")
    print("=" * 60)

    count = _ingest_markdown(
        client,
        pipeline_id,
        settings.DOCS_DIR,
        batch_size=args.batch_size,
        max_files=args.max_files,
        delay_sec=args.batch_delay,
    )
    print(f"Ingested {count} document(s). Waiting for indexing...")
    _wait_for_index(client, pipeline_id, timeout_sec=600)

    st = client.pipelines.get_status(pipeline_id=pipeline_id, full_details=True)
    fc = client.pipelines.files.get_status_counts(pipeline_id=pipeline_id)
    print(f"Status: {st.status}, files: {fc.counts}")

    r = client.pipelines.retrieve(
        pipeline_id=pipeline_id,
        query="satin trim spacing",
        dense_similarity_top_k=5,
        project_id=settings.LLAMA_CLOUD_PROJECT_ID,
    )
    n = len(r.retrieval_nodes or [])
    print(f"Test retrieve: {n} chunk(s)")
    if n == 0:
        print("Not ready yet — run: uv run python scripts/llamacloud_pipeline_status.py", pipeline_id)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
