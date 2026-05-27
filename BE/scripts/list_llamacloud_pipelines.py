#!/usr/bin/env python3
"""List LlamaCloud pipelines for the configured project (find real pipeline ID)."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import settings
from llama_cloud import AsyncLlamaCloud


async def main() -> None:
    if not settings.LLAMA_CLOUD_API_KEY:
        raise SystemExit("Set LLAMA_CLOUD_API_KEY in BE/.env")

    client = AsyncLlamaCloud(api_key=settings.LLAMA_CLOUD_API_KEY)
    kwargs: dict = {}
    if settings.LLAMA_CLOUD_PROJECT_ID:
        kwargs["project_id"] = settings.LLAMA_CLOUD_PROJECT_ID

    print("Listing pipelines...")
    if settings.LLAMA_CLOUD_PROJECT_ID:
        print(f"  project_id filter: {settings.LLAMA_CLOUD_PROJECT_ID}")
    else:
        print("  (no LLAMA_CLOUD_PROJECT_ID — listing all accessible pipelines)")

    try:
        pipelines = await client.pipelines.list(**kwargs)
    except Exception as exc:
        print(f"API error: {exc}")
        raise SystemExit(1) from exc

    if not pipelines:
        print("\nNo pipelines (indexes) found.")
        print("You likely only used Parse — create an Index first (see BE/README).")
        raise SystemExit(1)

    print(f"\nFound {len(pipelines)} pipeline(s):\n")
    for p in pipelines:
        pid = getattr(p, "id", None) or p.get("id") if isinstance(p, dict) else None
        name = getattr(p, "name", None) or (p.get("name") if isinstance(p, dict) else "?")
        ptype = getattr(p, "pipeline_type", None) or (
            p.get("pipeline_type") if isinstance(p, dict) else "?"
        )
        print(f"  name: {name}")
        print(f"  id:   {pid}  <-- use this as LLAMA_CLOUD_PIPELINE_ID")
        print(f"  type: {ptype}")
        print()

    if settings.LLAMA_CLOUD_PIPELINE_ID == settings.LLAMA_CLOUD_PROJECT_ID:
        print(
            "WARNING: LLAMA_CLOUD_PIPELINE_ID matches LLAMA_CLOUD_PROJECT_ID.\n"
            "That value is almost certainly the PROJECT id from Organization settings,\n"
            "not a pipeline id. Update .env with one of the pipeline id values above."
        )


if __name__ == "__main__":
    asyncio.run(main())
