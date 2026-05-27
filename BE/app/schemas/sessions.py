"""API schemas for anonymous session endpoints."""

import json
from typing import Any, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    source_file: Optional[str] = None
    source_url: Optional[str] = None
    section_title: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    sources: list[Source] = Field(default_factory=list)


class PreflightReport(BaseModel):
    content: str
    sources: list[Source] = Field(default_factory=list)


class CreateSessionResponse(BaseModel):
    session_id: str
    preflight: PreflightReport


class SessionDetailResponse(BaseModel):
    session_id: str
    design_report: dict[str, Any]
    preflight: PreflightReport
    chat_history: list[ChatMessage]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    sources: list[Source] = Field(default_factory=list)
    rag_status: str = "not_configured"
    rag_chunk_count: int = 0
    rag_detail: str | None = None


def _meta_str(meta: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        val = meta.get(key)
        if val is not None and str(val).strip():
            return str(val)
    return None


def sources_from_chunks(chunks: list[dict[str, Any]]) -> list[Source]:
    seen: set[tuple[str | None, str | None]] = set()
    out: list[Source] = []
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        source_file = _meta_str(
            meta, "source_file", "file_name", "filename", "doc_id", "document_id"
        )
        source_url = _meta_str(
            meta, "source_url", "file_path", "document_id", "pipeline_file_id"
        )
        section_title = _meta_str(
            meta, "section_title", "page_label", "header_path"
        )
        key = (source_file, section_title)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            Source(
                source_file=source_file,
                source_url=source_url,
                section_title=section_title,
            )
        )
    return out


def sources_to_json(sources: list[Source]) -> str:
    return json.dumps([s.model_dump() for s in sources])
