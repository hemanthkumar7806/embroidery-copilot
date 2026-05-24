"""RAG retrieval over the embroidery docs corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import settings
from app.core.logging import logger


class RAGService:
    """Chroma-backed retrieval for domain documentation."""

    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    @property
    def client(self) -> chromadb.PersistentClient:
        if self._client is None:
            self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.OPENAI_API_KEY,
                model_name=settings.EMBEDDING_MODEL,
            )
            self._collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                embedding_function=embedding_fn,
            )
        return self._collection

    @staticmethod
    def _chunk_markdown(file_path: Path, docs_root: Path) -> list[dict[str, Any]]:
        content = file_path.read_text(encoding="utf-8")
        chunks: list[dict[str, Any]] = []
        current_lines: list[str] = []
        section_title = file_path.stem
        rel = file_path.relative_to(docs_root).as_posix()

        for line in content.splitlines():
            if line.startswith("#"):
                if current_lines:
                    chunks.append(
                        {
                            "content": "\n".join(current_lines).strip(),
                            "metadata": {
                                "source_file": file_path.name,
                                "source_url": f"docs/{rel}",
                                "section_title": section_title,
                            },
                        }
                    )
                current_lines = [line]
                section_title = line.strip("# ").strip()
            else:
                current_lines.append(line)

        if current_lines:
            chunks.append(
                {
                    "content": "\n".join(current_lines).strip(),
                    "metadata": {
                        "source_file": file_path.name,
                        "source_url": f"docs/{rel}",
                        "section_title": section_title,
                    },
                }
            )
        return [c for c in chunks if c["content"]]

    def index_corpus(self, docs_dir: Path | None = None) -> int:
        docs_root = docs_dir or settings.DOCS_DIR
        if not docs_root.exists():
            raise FileNotFoundError(f"Docs directory not found: {docs_root}")

        md_files = sorted(docs_root.rglob("*.md"))
        documents: list[str] = []
        metadatas: list[dict[str, str]] = []
        ids: list[str] = []

        for md_file in md_files:
            for idx, chunk in enumerate(self._chunk_markdown(md_file, docs_root)):
                chunk_id = f"{md_file.stem}-{idx}"
                documents.append(chunk["content"])
                metadatas.append(chunk["metadata"])
                ids.append(chunk_id)

        if not documents:
            logger.warning("rag_index_empty", docs_root=str(docs_root))
            return 0

        try:
            self.client.delete_collection(settings.CHROMA_COLLECTION)
        except Exception:
            pass
        self._collection = None
        embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.EMBEDDING_MODEL,
        )
        self._collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            embedding_function=embedding_fn,
        )
        collection = self._collection
        batch_size = 64
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            self.collection.add(
                documents=documents[start:end],
                metadatas=metadatas[start:end],
                ids=ids[start:end],
            )
        logger.info("rag_indexed", chunks=len(documents), docs_root=str(docs_root))
        return len(documents)

    def retrieve(self, query_text: str, n_results: int = 8) -> list[dict[str, Any]]:
        if not settings.OPENAI_API_KEY:
            return []
        try:
            count = self.collection.count()
            if count == 0:
                return []
            results = self.collection.query(
                query_texts=[query_text],
                n_results=min(n_results, max(1, count)),
            )
        except Exception as exc:
            logger.warning("rag_retrieve_failed", error=str(exc))
            return []
        chunks: list[dict[str, Any]] = []
        if not results or not results.get("documents"):
            return chunks
        for idx in range(len(results["documents"][0])):
            chunks.append(
                {
                    "content": results["documents"][0][idx],
                    "metadata": results["metadatas"][0][idx] if results.get("metadatas") else {},
                }
            )
        return chunks

    @staticmethod
    def format_context(chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "No documentation chunks retrieved."
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata") or {}
            title = meta.get("section_title", meta.get("source_file", "doc"))
            source = meta.get("source_url", "")
            parts.append(f"[{i}] {title} ({source})\n{chunk.get('content', '')}")
        return "\n\n".join(parts)


rag_service = RAGService()
