"""RAG retrieval over LlamaCloud hosted index."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from llama_cloud import AsyncLlamaCloud

from app.core.config import settings
from app.core.logging import logger

RagStatus = Literal[
    "ok",
    "not_configured",
    "misconfigured",
    "api_error",
    "empty",
]


@dataclass(frozen=True)
class RagResult:
    status: RagStatus
    chunks: list[dict[str, Any]]
    detail: str = ""


def _node_metadata(node: Any) -> dict[str, Any]:
    """Extract metadata dict from a LlamaCloud TextNode."""
    if node is None:
        return {}
    extra = getattr(node, "extra_info", None) or getattr(node, "metadata", None)
    if isinstance(extra, dict):
        return dict(extra)
    return {}


def _normalize_chunk(node: Any, score: float | None) -> dict[str, Any]:
    meta = _node_metadata(node)
    text = getattr(node, "text", None) or ""
    source_file = (
        meta.get("file_name")
        or meta.get("filename")
        or meta.get("source_file")
        or meta.get("doc_id")
    )
    source_url = (
        meta.get("file_path")
        or meta.get("document_id")
        or meta.get("pipeline_file_id")
        or meta.get("source_url")
    )
    section_title = (
        meta.get("page_label")
        or meta.get("section_title")
        or meta.get("header_path")
    )
    normalized_meta: dict[str, Any] = {
        "source_file": source_file,
        "source_url": source_url,
        "section_title": section_title,
        **meta,
    }
    if score is not None:
        normalized_meta["score"] = score
    return {"content": text, "metadata": normalized_meta}


class RAGService:
    """LlamaCloud pipeline retrieval for domain documentation."""

    def __init__(self) -> None:
        self._client: AsyncLlamaCloud | None = None

    @property
    def client(self) -> AsyncLlamaCloud:
        if self._client is None:
            self._client = AsyncLlamaCloud(api_key=settings.LLAMA_CLOUD_API_KEY)
        return self._client

    def config_status(self) -> tuple[RagStatus, str]:
        if not settings.LLAMA_CLOUD_API_KEY:
            return "not_configured", "LLAMA_CLOUD_API_KEY is not set."
        if not settings.LLAMA_CLOUD_PIPELINE_ID:
            return "not_configured", "LLAMA_CLOUD_PIPELINE_ID is not set."
        if settings.rag_pipeline_misconfigured:
            return (
                "misconfigured",
                "LLAMA_CLOUD_PIPELINE_ID matches PROJECT_ID — use your Index pipeline UUID, not the project ID.",
            )
        return "ok", ""

    async def retrieve(self, query_text: str, n_results: int | None = None) -> RagResult:
        cfg_status, cfg_detail = self.config_status()
        if cfg_status != "ok":
            logger.warning("rag_not_configured", status=cfg_status, detail=cfg_detail)
            return RagResult(status=cfg_status, chunks=[], detail=cfg_detail)

        top_k = n_results if n_results is not None else settings.LLAMA_CLOUD_RETRIEVAL_TOP_K
        try:
            kwargs: dict[str, Any] = {
                "pipeline_id": settings.LLAMA_CLOUD_PIPELINE_ID,
                "query": query_text,
                "dense_similarity_top_k": top_k,
                "enable_reranking": settings.LLAMA_CLOUD_ENABLE_RERANKING,
                "rerank_top_n": top_k,
            }
            if settings.LLAMA_CLOUD_PROJECT_ID:
                kwargs["project_id"] = settings.LLAMA_CLOUD_PROJECT_ID

            results = await self.client.pipelines.retrieve(**kwargs)
        except Exception as exc:
            detail = str(exc)
            logger.warning("rag_retrieve_failed", error=detail)
            return RagResult(status="api_error", chunks=[], detail=detail)

        chunks: list[dict[str, Any]] = []
        for item in results.retrieval_nodes or []:
            node = getattr(item, "node", None)
            score = getattr(item, "score", None)
            chunk = _normalize_chunk(node, score)
            if chunk["content"]:
                chunks.append(chunk)

        if not chunks:
            logger.warning("rag_retrieve_empty", query_len=len(query_text))
            return RagResult(
                status="empty",
                chunks=[],
                detail="LlamaCloud returned no chunks. Create an Index and ingest documents, or check pipeline ID.",
            )

        logger.info("rag_retrieved", query_len=len(query_text), chunks=len(chunks))
        return RagResult(status="ok", chunks=chunks)

    @staticmethod
    def format_context(chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "No documentation chunks retrieved."
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata") or {}
            title = meta.get("section_title", meta.get("source_file", "doc"))
            source = meta.get("source_url", meta.get("source_file", ""))
            score = meta.get("score")
            score_str = f", score={score:.3f}" if isinstance(score, (int, float)) else ""
            parts.append(f"[{i}] {title} ({source}{score_str})\n{chunk.get('content', '')}")
        return "\n\n".join(parts)


rag_service = RAGService()
