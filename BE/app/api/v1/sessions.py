"""Anonymous session endpoints for SVG upload, preflight, and chat."""

import json
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging import logger
from app.schemas.sessions import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    PreflightReport,
    SessionDetailResponse,
    Source,
    rule_engine_from_dict,
    sources_from_chunks,
    sources_to_json,
)
from app.services.chat_service import generate_chat_reply
from app.services.database import database_service
from app.services.rule_engine import run as run_rule_engine
from app.services.svg_parser import (
    build_design_report,
    design_report_to_json,
    empty_design_report,
)
from app.services.welcome import build_chat_only_welcome, build_welcome_message

router = APIRouter()

EMPTY_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>'


def _load_sources(raw: str | None) -> list[Source]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [Source(**item) for item in data]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def _preflight_from_message(content: str, sources_raw: str | None) -> PreflightReport:
    return PreflightReport(content=content, sources=_load_sources(sources_raw))


@router.post("/chat", response_model=CreateSessionResponse)
async def create_chat_session() -> CreateSessionResponse:
    """Start a general embroidery Q&A session without uploading an SVG."""
    session_id = str(uuid.uuid4())
    svg_path = settings.DATA_DIR / "svgs" / f"{session_id}.svg"
    svg_path.write_bytes(EMPTY_SVG)

    design_report = empty_design_report()
    design_report_json = design_report_to_json(design_report)
    welcome = build_chat_only_welcome()
    preflight = PreflightReport(content=welcome, sources=[])

    database_service.create_session(
        session_id=session_id,
        svg_path=str(svg_path),
        design_report_json=design_report_json,
        preflight_json="[]",
        preflight_content=welcome,
    )
    logger.info("chat_session_created", session_id=session_id)
    return CreateSessionResponse(session_id=session_id, preflight=preflight)


@router.post("", response_model=CreateSessionResponse)
async def create_session(svg_file: UploadFile = File(...)) -> CreateSessionResponse:
    if not svg_file.filename or not svg_file.filename.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Upload must be an .svg file.")

    raw = await svg_file.read()
    if len(raw) > settings.MAX_SVG_BYTES:
        raise HTTPException(status_code=413, detail=f"SVG exceeds {settings.MAX_SVG_BYTES} bytes.")

    session_id = str(uuid.uuid4())
    svg_path = settings.DATA_DIR / "svgs" / f"{session_id}.svg"
    svg_path.write_bytes(raw)

    design_report = build_design_report(raw, document_name=svg_file.filename)
    rules_payload = run_rule_engine(design_report)
    design_report["cached_rule_engine"] = rules_payload
    design_report_json = design_report_to_json(design_report)

    welcome_content = build_welcome_message(design_report, rules_payload)
    preflight = PreflightReport(
        content=welcome_content,
        sources=[],
        rule_engine=rule_engine_from_dict(rules_payload),
    )

    database_service.create_session(
        session_id=session_id,
        svg_path=str(svg_path),
        design_report_json=design_report_json,
        preflight_json="[]",
        preflight_content=welcome_content,
    )
    logger.info("session_created", session_id=session_id)
    return CreateSessionResponse(session_id=session_id, preflight=preflight)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str) -> SessionDetailResponse:
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    database_service.touch_session(session_id)
    messages = database_service.get_messages(session_id)
    first = messages[0] if messages else None
    preflight = _preflight_from_message(first.content if first else "", first.sources_json if first else None)

    chat_history = [
        ChatMessage(role=m.role, content=m.content, sources=_load_sources(m.sources_json))
        for m in messages
    ]
    return SessionDetailResponse(
        session_id=session_id,
        design_report=json.loads(row.design_report_json),
        preflight=preflight,
        chat_history=chat_history,
    )


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat_session(session_id: str, body: ChatRequest) -> ChatResponse:
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    history = database_service.get_messages(session_id)
    design_report = json.loads(row.design_report_json)
    database_service.add_message(session_id, "user", body.message)

    try:
        reply, chunks, rag_status, rag_detail, rules_payload, updated_report = (
            await generate_chat_reply(design_report, history, body.message)
        )
    except Exception as exc:
        logger.exception("chat_generation_failed", session_id=session_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to generate chat response.") from exc

    database_service.update_design_report(session_id, design_report_to_json(updated_report))
    sources = sources_from_chunks(chunks)
    database_service.add_message(session_id, "assistant", reply, sources_to_json(sources))
    return ChatResponse(
        content=reply,
        sources=sources,
        rag_status=rag_status,
        rag_chunk_count=len(chunks),
        rag_detail=rag_detail or None,
        rule_engine=rule_engine_from_dict(rules_payload),
    )


@router.get("/{session_id}/svg")
async def get_session_svg(session_id: str) -> FileResponse:
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return FileResponse(row.svg_path, media_type="image/svg+xml")


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    if not database_service.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"message": "Session deleted."}
