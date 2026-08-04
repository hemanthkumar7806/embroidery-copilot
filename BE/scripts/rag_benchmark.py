"""RAG index benchmark — validate retrieval quality before building citations.

Hits the live LlamaCloud index (network + credentials). NOT a CI unit test; run manually:

    cd BE && uv run python scripts/rag_benchmark.py

For each representative embroidery query it prints chunk count and the top sources, so we
can confirm the index consistently returns relevant docs before citations are built on it.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag import rag_service  # noqa: E402

QUERIES: list[str] = [
    "fill stitch density mm spacing for cotton and knit fabric",
    "satin column minimum width for embroidery",
    "underlay types for fleece and stretchy knit fabric",
    "pull compensation for stretch fabric embroidery",
    "minimum stitch length running stitch vs satin",
    "small text lettering minimum size embroidery",
    "trims and jump stitches embroidery routing",
    "stabilizer choice by fabric type embroidery",
]


async def main() -> None:
    cfg_status, cfg_detail = rag_service.config_status()
    print(f"RAG config: {cfg_status} {cfg_detail}".rstrip())
    if cfg_status != "ok":
        print("Index not configured — cannot benchmark.")
        return

    healthy = 0
    for query in QUERIES:
        result = await rag_service.retrieve(query, n_results=4)
        n = len(result.chunks)
        print(f"\n[{result.status}] ({n} chunks) {query}")
        if result.status != "ok":
            print(f"    detail: {result.detail}")
            continue
        if n:
            healthy += 1
        for chunk in result.chunks[:3]:
            meta = chunk.get("metadata") or {}
            src = meta.get("source_file") or "?"
            sec = meta.get("section_title") or ""
            score = meta.get("score")
            score_str = f" score={score:.3f}" if isinstance(score, (int, float)) else ""
            print(f"    - {src} :: {sec}{score_str}")

    print(f"\n=== {healthy}/{len(QUERIES)} queries returned chunks ===")


if __name__ == "__main__":
    asyncio.run(main())
