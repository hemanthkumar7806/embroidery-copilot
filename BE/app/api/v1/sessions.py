"""Anonymous session endpoints for SVG upload, preflight, and chat."""

import json
import time
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.logging import logger
from app.services import analytics
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
from app.services.issue_element_mapper import enrich_rule_engine_payload
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


def _build_rules_payload(design_report: dict) -> dict:
    rules_payload = run_rule_engine(design_report)
    return enrich_rule_engine_payload(design_report, rules_payload)


def _svg_summary(design_report: dict) -> tuple[float | None, float | None, int | None]:
    """(width_mm, height_mm, element_count) from a parsed design report."""
    summary = design_report.get("summary") or {}
    page = summary.get("page_size_mm") or {}
    return page.get("w"), page.get("h"), summary.get("element_count")


def _source_from_request(request: Request) -> str:
    """Best-effort acquisition source. The Inkscape extension uploads via curl."""
    explicit = request.query_params.get("from")
    if explicit:
        return explicit
    ua = (getattr(request.state, "user_agent", None) or "").lower()
    if "curl" in ua or "python-urllib" in ua or "python-requests" in ua:
        return "inkscape"
    return "web"


def _process_svg(raw: bytes, filename: str) -> tuple[dict, dict, str, str]:
    """CPU-bound SVG parse + rule engine + welcome. Run in a threadpool.

    These are synchronous and heavy; running them off the event loop keeps the
    single Render worker responsive when the browser and extension hit at once.
    """
    design_report = build_design_report(raw, document_name=filename)
    rules_payload = _build_rules_payload(design_report)
    design_report["cached_rule_engine"] = rules_payload
    design_report_json = design_report_to_json(design_report)
    welcome_content = build_welcome_message(design_report, rules_payload)
    return design_report, rules_payload, design_report_json, welcome_content


@router.post("/chat", response_model=CreateSessionResponse)
async def create_chat_session(request: Request) -> CreateSessionResponse:
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

    visitor_id = getattr(request.state, "visitor_id", None)
    ip = getattr(request.state, "client_ip", None)
    ua = getattr(request.state, "user_agent", None)
    analytics.get_or_create_visitor(visitor_id, ip, ua, getattr(request.state, "referrer", None))
    analytics.record_session(
        session_id=session_id,
        kind="chat_only",
        source=_source_from_request(request),
        ip=ip,
        user_agent=ua,
        visitor_id=visitor_id,
    )
    analytics.link_visitor_to_session(session_id, visitor_id, ip, ua)
    analytics.record_event("session_created", visitor_id=visitor_id, session_id=session_id, ip=ip,
                           meta={"kind": "chat_only"})
    return CreateSessionResponse(session_id=session_id, preflight=preflight)


@router.post("", response_model=CreateSessionResponse)
async def create_session(request: Request, svg_file: UploadFile = File(...)) -> CreateSessionResponse:
    if not svg_file.filename or not svg_file.filename.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Upload must be an .svg file.")

    raw = await svg_file.read()
    if len(raw) > settings.MAX_SVG_BYTES:
        raise HTTPException(status_code=413, detail=f"SVG exceeds {settings.MAX_SVG_BYTES} bytes.")

    started = time.perf_counter()
    session_id = str(uuid.uuid4())
    svg_path = settings.DATA_DIR / "svgs" / f"{session_id}.svg"
    await run_in_threadpool(svg_path.write_bytes, raw)
    t_write = time.perf_counter()

    design_report, rules_payload, design_report_json, welcome_content = await run_in_threadpool(
        _process_svg, raw, svg_file.filename
    )
    t_process = time.perf_counter()

    preflight = PreflightReport(
        content=welcome_content,
        sources=[],
        rule_engine=rule_engine_from_dict(rules_payload),
    )

    await run_in_threadpool(
        database_service.create_session,
        session_id,
        str(svg_path),
        design_report_json,
        "[]",
        welcome_content,
    )
    t_db = time.perf_counter()
    logger.info(
        "session_created",
        session_id=session_id,
        write_ms=round((t_write - started) * 1000),
        process_ms=round((t_process - t_write) * 1000),
        db_ms=round((t_db - t_process) * 1000),
        total_ms=round((t_db - started) * 1000),
        bytes=len(raw),
    )

    # Uploads arrive server-side from the extension (no browser cookie), so the
    # visitor is linked later when the browser opens the session. Capture the
    # user's IP/UA and the full SVG for permanent analytics here.
    ip = getattr(request.state, "client_ip", None)
    ua = getattr(request.state, "user_agent", None)
    width_mm, height_mm, element_count = _svg_summary(design_report)
    rule_status, issue_count, top_issues = analytics.summarize_rules(rules_payload)
    svg_text = raw.decode("utf-8", errors="replace")
    analytics.record_session(
        session_id=session_id,
        kind="svg",
        source=_source_from_request(request),
        filename=svg_file.filename,
        svg_bytes=len(raw),
        svg_width_mm=width_mm,
        svg_height_mm=height_mm,
        element_count=element_count,
        svg_text=svg_text,
        rule_status=rule_status,
        issue_count=issue_count,
        top_issues=top_issues,
        process_ms=round((t_process - t_write) * 1000),
        total_ms=round((t_db - started) * 1000),
        ip=ip,
        user_agent=ua,
    )
    analytics.record_event("session_created", session_id=session_id, ip=ip,
                           meta={"kind": "svg", "filename": svg_file.filename, "bytes": len(raw)})
    analytics.record_event("svg_uploaded", session_id=session_id, ip=ip,
                           meta={"filename": svg_file.filename, "bytes": len(raw),
                                 "element_count": element_count, "rule_status": rule_status})
    return CreateSessionResponse(session_id=session_id, preflight=preflight)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, request: Request) -> SessionDetailResponse:
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    database_service.touch_session(session_id)

    # First browser touch: mint/read the visitor cookie and link it to the
    # session that the extension created server-side.
    visitor_id = getattr(request.state, "visitor_id", None)
    ip = getattr(request.state, "client_ip", None)
    ua = getattr(request.state, "user_agent", None)
    analytics.get_or_create_visitor(visitor_id, ip, ua, getattr(request.state, "referrer", None))
    analytics.link_visitor_to_session(session_id, visitor_id, ip, ua)
    analytics.record_event("session_opened", visitor_id=visitor_id, session_id=session_id, ip=ip)
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
async def chat_session(session_id: str, body: ChatRequest, request: Request) -> ChatResponse:
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    visitor_id = getattr(request.state, "visitor_id", None)
    ip = getattr(request.state, "client_ip", None)
    ua = getattr(request.state, "user_agent", None)
    analytics.get_or_create_visitor(visitor_id, ip, ua, getattr(request.state, "referrer", None))
    analytics.link_visitor_to_session(session_id, visitor_id, ip, ua)

    history = database_service.get_messages(session_id)
    design_report = json.loads(row.design_report_json)
    database_service.add_message(session_id, "user", body.message)
    analytics.record_message(
        session_id=session_id, visitor_id=visitor_id, role="user", content=body.message
    )

    chat_started = time.perf_counter()
    try:
        reply, chunks, rag_status, rag_detail, rules_payload, updated_report = (
            await generate_chat_reply(design_report, history, body.message)
        )
    except Exception as exc:
        logger.exception("chat_generation_failed", session_id=session_id, error=str(exc))
        analytics.record_event(
            "chat_error", visitor_id=visitor_id, session_id=session_id, ip=ip,
            meta={"error": str(exc)[:500]},
        )
        raise HTTPException(status_code=502, detail="Failed to generate chat response.") from exc
    latency_ms = round((time.perf_counter() - chat_started) * 1000)

    database_service.update_design_report(session_id, design_report_to_json(updated_report))
    sources = sources_from_chunks(chunks)
    database_service.add_message(session_id, "assistant", reply, sources_to_json(sources))
    analytics.record_message(
        session_id=session_id, visitor_id=visitor_id, role="assistant", content=reply,
        latency_ms=latency_ms, rag_status=rag_status, rag_chunk_count=len(chunks),
    )
    return ChatResponse(
        content=reply,
        sources=sources,
        rag_status=rag_status,
        rag_chunk_count=len(chunks),
        rag_detail=rag_detail or None,
        rule_engine=rule_engine_from_dict(rules_payload),
    )


@router.post("/{session_id}/svg", response_model=CreateSessionResponse)
async def upload_session_svg(
    session_id: str, request: Request, svg_file: UploadFile = File(...)
) -> CreateSessionResponse:
    """Upload or replace SVG on an existing session; append welcome message, keep chat history."""
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    if not svg_file.filename or not svg_file.filename.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Upload must be an .svg file.")

    raw = await svg_file.read()
    if len(raw) > settings.MAX_SVG_BYTES:
        raise HTTPException(status_code=413, detail=f"SVG exceeds {settings.MAX_SVG_BYTES} bytes.")

    svg_path = settings.DATA_DIR / "svgs" / f"{session_id}.svg"
    await run_in_threadpool(svg_path.write_bytes, raw)

    design_report, rules_payload, design_report_json, welcome_content = await run_in_threadpool(
        _process_svg, raw, svg_file.filename
    )

    preflight = PreflightReport(
        content=welcome_content,
        sources=[],
        rule_engine=rule_engine_from_dict(rules_payload),
    )

    await run_in_threadpool(database_service.update_design_report, session_id, design_report_json)
    await run_in_threadpool(
        database_service.add_message, session_id, "assistant", welcome_content, "[]"
    )
    logger.info("session_svg_uploaded", session_id=session_id, filename=svg_file.filename)

    ip = getattr(request.state, "client_ip", None)
    width_mm, height_mm, element_count = _svg_summary(design_report)
    rule_status, issue_count, top_issues = analytics.summarize_rules(rules_payload)
    analytics.update_session_svg(
        session_id=session_id,
        filename=svg_file.filename,
        svg_bytes=len(raw),
        svg_width_mm=width_mm,
        svg_height_mm=height_mm,
        element_count=element_count,
        svg_text=raw.decode("utf-8", errors="replace"),
        rule_status=rule_status,
        issue_count=issue_count,
        top_issues=top_issues,
    )
    analytics.record_event("svg_replaced", session_id=session_id, ip=ip,
                           meta={"filename": svg_file.filename, "bytes": len(raw)})
    return CreateSessionResponse(session_id=session_id, preflight=preflight)


@router.get("/{session_id}/svg")
async def get_session_svg(session_id: str) -> FileResponse:
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return FileResponse(row.svg_path, media_type="image/svg+xml")


@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request) -> dict[str, str]:
    if not database_service.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    analytics.record_event(
        "session_deleted",
        visitor_id=getattr(request.state, "visitor_id", None),
        session_id=session_id,
        ip=getattr(request.state, "client_ip", None),
    )
    return {"message": "Session deleted."}
