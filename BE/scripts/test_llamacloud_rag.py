#!/usr/bin/env python3
"""Test LlamaCloud RAG retrieval with credentials from .env."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import settings
from app.services.rag import rag_service


async def main() -> None:
    if not settings.has_rag:
        raise SystemExit(
            "Set LLAMA_CLOUD_API_KEY and LLAMA_CLOUD_PIPELINE_ID in BE/.env"
        )

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "satin column spacing trim"
    print(f"Query: {query}\n")

    rag = await rag_service.retrieve(query)
    print(f"RAG status: {rag.status}")
    if rag.detail:
        print(f"Detail: {rag.detail}")
    chunks = rag.chunks
    if rag.status != "ok":
        raise SystemExit(1)

    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata") or {}
        title = meta.get("section_title") or meta.get("source_file") or "doc"
        source = meta.get("source_url") or meta.get("source_file") or ""
        score = meta.get("score")
        score_str = f" score={score:.3f}" if isinstance(score, (int, float)) else ""
        print(f"--- [{i}] {title} ({source}){score_str} ---")
        text = chunk.get("content", "")
        print(text[:500] + ("..." if len(text) > 500 else ""))
        print()

    print(f"Retrieved {len(chunks)} chunk(s).")


if __name__ == "__main__":
    asyncio.run(main())
