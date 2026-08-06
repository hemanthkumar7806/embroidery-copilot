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


class RuleIssueOut(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    detail: str
    suggested_action: str
    source: str
    confidence: float | None = None
    # Capability tier: "auto_fix" (🟢) / "guided" (🟡) / "recommendation" (🔵).
    capability: str = "recommendation"
    # Structured auto-fix operation for 🟢 issues (op/attribute/value/target_ids/summary).
    fix: dict[str, Any] | None = None
    group: str | None = None
    element_ids: list[str] = Field(default_factory=list)
    focus_bbox: dict[str, float] | None = None
    # Per-shape breakdown: one entry per affected element_id, each with its own tight
    # focus_bbox and (for 🟢 issues) its own single-target fix — lets the UI zoom to and
    # fix one shape at a time instead of only the group as a whole.
    instances: list[dict[str, Any]] = Field(default_factory=list)
    evidence: dict[str, Any] | None = None
    # Documentation citations backing this finding (AI review findings only).
    sources: list[Source] = Field(default_factory=list)


class RuleDecisionOut(BaseModel):
    status: str
    reason: str
    main_problem: str | None = None
    next_action: str | None = None


class RuleEngineOut(BaseModel):
    decision: RuleDecisionOut
    issues: list[RuleIssueOut] = Field(default_factory=list)
    context_gaps: list[RuleIssueOut] = Field(default_factory=list)
    root_cause: dict[str, Any] | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class PreflightReport(BaseModel):
    content: str
    sources: list[Source] = Field(default_factory=list)
    rule_engine: RuleEngineOut | None = None


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
    # The finding the user currently has selected/highlighted in the UI, if any — lets the
    # backend answer "how do I fix this" unambiguously instead of asking which finding "this" is.
    selected_finding_id: Optional[str] = None


class SetContextRequest(BaseModel):
    """Explicitly set project context (fabric/garment/hoop) for a session."""

    fabric_type: Optional[str] = None
    garment_type: Optional[str] = None
    hoop_size_mm: Optional[dict[str, float]] = None


class SetContextResponse(BaseModel):
    session_context: dict[str, Any] = Field(default_factory=dict)
    rule_engine: RuleEngineOut | None = None


class AiReviewResponse(BaseModel):
    rule_engine: RuleEngineOut | None = None
    ai_reviewed: bool = True
    ai_count: int = 0


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    sources: list[Source] = Field(default_factory=list)
    rag_status: str = "not_configured"
    rag_chunk_count: int = 0
    rag_detail: str | None = None
    rule_engine: RuleEngineOut | None = None


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


def rule_engine_from_dict(payload: dict[str, Any] | None) -> RuleEngineOut | None:
    if not payload:
        return None

    decision_payload = payload.get("decision") or {}
    detailed = payload.get("detailed_decision") or {}
    issues = [
        RuleIssueOut(
            id=issue.get("id", ""),
            category=issue.get("category", ""),
            severity=issue.get("severity", ""),
            title=issue.get("title", ""),
            detail=issue.get("detail", ""),
            suggested_action=issue.get("suggested_action", ""),
            source=issue.get("source", ""),
            confidence=issue.get("confidence"),
            capability=issue.get("capability", "recommendation"),
            fix=issue.get("fix"),
            group=issue.get("group"),
            element_ids=list(issue.get("element_ids") or []),
            focus_bbox=issue.get("focus_bbox"),
            instances=list(issue.get("instances") or []),
            evidence=issue.get("evidence"),
            sources=[Source(**s) for s in (issue.get("sources") or []) if isinstance(s, dict)],
        )
        for issue in payload.get("issues") or []
    ]
    context_gaps = [
        RuleIssueOut(
            id=issue.get("id", ""),
            category=issue.get("category", ""),
            severity=issue.get("severity", ""),
            title=issue.get("title", ""),
            detail=issue.get("detail", ""),
            suggested_action=issue.get("suggested_action", ""),
            source=issue.get("source", ""),
            confidence=issue.get("confidence"),
            capability=issue.get("capability", "recommendation"),
            fix=issue.get("fix"),
            group=issue.get("group"),
            element_ids=list(issue.get("element_ids") or []),
            focus_bbox=issue.get("focus_bbox"),
            instances=list(issue.get("instances") or []),
            evidence=issue.get("evidence"),
            sources=[Source(**s) for s in (issue.get("sources") or []) if isinstance(s, dict)],
        )
        for issue in payload.get("context_gaps") or []
    ]
    return RuleEngineOut(
        decision=RuleDecisionOut(
            status=decision_payload.get("status", "SAFE_TO_TEST"),
            reason=decision_payload.get("reason", ""),
            main_problem=detailed.get("main_problem"),
            next_action=detailed.get("next_action"),
        ),
        issues=issues,
        context_gaps=context_gaps,
        root_cause=payload.get("root_cause"),
        summary=payload.get("summary") or {},
    )
