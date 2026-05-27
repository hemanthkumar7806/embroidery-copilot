#!/usr/bin/env python3
"""Re-ingest docs into an existing pipeline in small batches (avoids Gemini 429)."""

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

DEFAULT_PIPELINE_ID = "ecc9c499-285a-445e-a13e-40ba7eff0481"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-id", default=settings.LLAMA_CLOUD_PIPELINE_ID or DEFAULT_PIPELINE_ID)
    parser.add_argument("--batch-size", type=int, default=5, help="Docs per batch (keep low for free Gemini embed quota)")
    parser.add_argument("--delay", type=int, default=90, help="Seconds between batches")
    parser.add_argument("--max-files", type=int, default=15, help="Max markdown files to ingest this run")
    args = parser.parse_args()

    if not settings.LLAMA_CLOUD_API_KEY:
        raise SystemExit("Set LLAMA_CLOUD_API_KEY in BE/.env")

    client = LlamaCloud(api_key=settings.LLAMA_CLOUD_API_KEY)
    pid = args.pipeline_id

    md_files = sorted(settings.DOCS_DIR.rglob("*.md"))[: args.max_files]
    if not md_files:
        raise SystemExit(f"No .md files in {settings.DOCS_DIR}")

    print(f"Pipeline {pid}: ingesting {len(md_files)} file(s) in batches of {args.batch_size}...")

    for start in range(0, len(md_files), args.batch_size):
        batch = md_files[start : start + args.batch_size]
        body = []
        for path in batch:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            rel = path.relative_to(settings.DOCS_DIR).as_posix()
            body.append(
                {
                    "text": text[:200_000],
                    "metadata": {"source_file": path.name, "source_url": f"docs/{rel}"},
                }
            )
        if not body:
            continue
        print(f"  batch {start // args.batch_size + 1}: {len(body)} doc(s)...")
        try:
            client.pipelines.documents.create(pipeline_id=pid, body=body)
        except Exception as exc:
            if "402" in str(exc) and "50" in str(exc):
                raise SystemExit(
                    "Org file limit reached (50 on free tier). "
                    "Run: uv run python scripts/reset_llamacloud_pipeline.py"
                ) from exc
            raise
        client.pipelines.sync.create(pipeline_id=pid)
        if start + args.batch_size < len(md_files):
            print(f"  waiting {args.delay}s (Gemini embed rate limit)...")
            time.sleep(args.delay)

    print("\nDone. Check status:")
    print(f"  uv run python scripts/llamacloud_pipeline_status.py {pid}")


if __name__ == "__main__":
    main()
