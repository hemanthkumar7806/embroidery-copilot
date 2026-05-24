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


def sources_from_chunks(chunks: list[dict[str, Any]]) -> list[Source]:
    out: list[Source] = []
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        out.append(
            Source(
                source_file=meta.get("source_file"),
                source_url=meta.get("source_url"),
                section_title=meta.get("section_title"),
            )
        )
    return out


def sources_to_json(sources: list[Source]) -> str:
    return json.dumps([s.model_dump() for s in sources])
