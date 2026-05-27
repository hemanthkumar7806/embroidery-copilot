#!/usr/bin/env python3
"""Upload combined bundle files from data/llamacloud_bundles/ to LlamaCloud pipeline."""

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

BUNDLE_DIR = settings.DATA_DIR / "llamacloud_bundles"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-id", default=settings.LLAMA_CLOUD_PIPELINE_ID)
    parser.add_argument("--delay", type=int, default=60, help="Seconds between bundles (Gemini embed quota)")
    args = parser.parse_args()

    if not args.pipeline_id:
        raise SystemExit("Set LLAMA_CLOUD_PIPELINE_ID in BE/.env")
    if not settings.LLAMA_CLOUD_API_KEY:
        raise SystemExit("Set LLAMA_CLOUD_API_KEY in BE/.env")

    bundles = sorted(BUNDLE_DIR.glob("*.md"))
    if not bundles:
        raise SystemExit(f"No bundles found. Run: uv run python scripts/build_llamacloud_bundles.py")

    client = LlamaCloud(api_key=settings.LLAMA_CLOUD_API_KEY)
    print(f"Ingesting {len(bundles)} bundle(s) into pipeline {args.pipeline_id}...")

    for i, path in enumerate(bundles, start=1):
        text = path.read_text(encoding="utf-8")
        print(f"  [{i}/{len(bundles)}] {path.name} ({len(text)//1024} KB)...")
        client.pipelines.documents.create(
            pipeline_id=args.pipeline_id,
            body=[
                {
                    "text": text[:500_000],
                    "metadata": {
                        "source_file": path.name,
                        "source_url": f"llamacloud_bundles/{path.name}",
                        "bundle": True,
                    },
                }
            ],
        )
        client.pipelines.sync.create(pipeline_id=args.pipeline_id)
        if i < len(bundles):
            print(f"  waiting {args.delay}s...")
            time.sleep(args.delay)

    print("\nDone. Test with:")
    print('  uv run python scripts/test_llamacloud_rag.py "satin trim spacing"')


if __name__ == "__main__":
    main()
