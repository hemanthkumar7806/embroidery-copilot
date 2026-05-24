#!/usr/bin/env python3
"""One-shot corpus indexing for RAG."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import settings
from app.services.rag import rag_service


def main() -> None:
    if not settings.OPENAI_API_KEY:
        raise SystemExit("OPENAI_API_KEY is required to build embeddings.")
    count = rag_service.index_corpus(settings.DOCS_DIR)
    print(f"Indexed {count} chunks from {settings.DOCS_DIR}")


if __name__ == "__main__":
    main()
