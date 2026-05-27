#!/usr/bin/env python3
"""Create a LlamaCloud Index (pipeline) and optionally ingest local docs.

Usage:
  uv run python scripts/create_llamacloud_pipeline.py
  uv run python scripts/create_llamacloud_pipeline.py --ingest-docs
  uv run python scripts/create_llamacloud_pipeline.py --name embroidery-rag

Prints LLAMA_CLOUD_PIPELINE_ID to add to BE/.env.
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

DEFAULT_PIPELINE_NAME = "embroidery-rag"


def _embedding_config() -> dict:
    """Prefer Gemini embeddings if user already uses Gemini for chat."""
    if settings.GEMINI_API_KEY:
        return {
            "type": "GEMINI_EMBEDDING",
            "component": {
                "api_key": settings.GEMINI_API_KEY,
                "model_name": "gemini-embedding-001",
                "embed_batch_size": 10,
            },
        }
    if settings.OPENAI_API_KEY:
        return {
            "type": "OPENAI_EMBEDDING",
            "component": {
                "api_key": settings.OPENAI_API_KEY,
                "model_name": "text-embedding-3-small",
                "embed_batch_size": 10,
            },
        }
    raise SystemExit(
        "Set GEMINI_API_KEY or OPENAI_API_KEY in BE/.env for Index embeddings."
    )


def _ingest_markdown(
    client: LlamaCloud,
    pipeline_id: str,
    docs_dir: Path,
    *,
    batch_size: int = 5,
    max_files: int = 15,
    delay_sec: int = 90,
) -> int:
    md_files = sorted(docs_dir.rglob("*.md"))[:max_files]
    if not md_files:
        print(f"No .md files under {docs_dir}")
        return 0

    total = 0
    for start in range(0, len(md_files), batch_size):
        batch = md_files[start : start + batch_size]
        body = []
        for path in batch:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            rel = path.relative_to(docs_dir).as_posix()
            body.append(
                {
                    "text": text[:200_000],
                    "metadata": {"source_file": path.name, "source_url": f"docs/{rel}"},
                }
            )
        if not body:
            continue
        print(f"Uploading batch {start // batch_size + 1} ({len(body)} doc(s))...")
        client.pipelines.documents.create(pipeline_id=pipeline_id, body=body)
        client.pipelines.sync.create(pipeline_id=pipeline_id)
        total += len(body)
        if start + batch_size < len(md_files):
            print(f"Waiting {delay_sec}s (avoid Gemini embedding rate limits)...")
            time.sleep(delay_sec)
    return total


def _wait_for_index(client: LlamaCloud, pipeline_id: str, timeout_sec: int = 300) -> None:
    print("Waiting for indexing (may take a few minutes)...")
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status = client.pipelines.get_status(pipeline_id=pipeline_id)
        state = getattr(status, "status", None) or str(status)
        print(f"  status: {state}")
        if state not in ("NOT_STARTED", "IN_PROGRESS", "PENDING"):
            return
        time.sleep(10)
    print("Timed out waiting for index — check LlamaCloud dashboard.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create LlamaCloud RAG pipeline")
    parser.add_argument("--name", default=DEFAULT_PIPELINE_NAME, help="Pipeline name")
    parser.add_argument(
        "--ingest-docs",
        action="store_true",
        help=f"Ingest *.md from DOCS_DIR ({settings.DOCS_DIR})",
    )
    parser.add_argument("--no-wait", action="store_true", help="Skip waiting for index status")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--max-files", type=int, default=15)
    parser.add_argument("--batch-delay", type=int, default=90)
    args = parser.parse_args()

    if not settings.LLAMA_CLOUD_API_KEY:
        raise SystemExit("Set LLAMA_CLOUD_API_KEY in BE/.env")
    if not settings.LLAMA_CLOUD_PROJECT_ID:
        raise SystemExit("Set LLAMA_CLOUD_PROJECT_ID in BE/.env (Organization → Overview)")

    client = LlamaCloud(api_key=settings.LLAMA_CLOUD_API_KEY)

    print(f"Creating pipeline '{args.name}' in project {settings.LLAMA_CLOUD_PROJECT_ID}...")
    pipeline = client.pipelines.upsert(
        name=args.name,
        project_id=settings.LLAMA_CLOUD_PROJECT_ID,
        pipeline_type="MANAGED",
        embedding_config=_embedding_config(),
        # "fast" for markdown — agentic costs more credits and is for PDFs/images
        llama_parse_parameters={"tier": "fast", "version": "latest"},
        transform_config={"mode": "auto", "chunk_size": 1024, "chunk_overlap": 128},
    )

    pipeline_id = pipeline.id
    print()
    print("=" * 60)
    print("SUCCESS — add this to BE/.env:")
    print(f"LLAMA_CLOUD_PIPELINE_ID={pipeline_id}")
    print("=" * 60)
    print()

    if args.ingest_docs:
        count = _ingest_markdown(
            client,
            pipeline_id,
            settings.DOCS_DIR,
            batch_size=args.batch_size,
            max_files=args.max_files,
            delay_sec=args.batch_delay,
        )
        if count and not args.no_wait:
            _wait_for_index(client, pipeline_id)
    else:
        print("Next: upload files in LlamaCloud, or run with --ingest-docs to load local markdown.")
        print("Then: uv run python scripts/test_llamacloud_rag.py \"satin trim spacing\"")


if __name__ == "__main__":
    main()
