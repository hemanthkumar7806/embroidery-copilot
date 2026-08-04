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
    AiReviewResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    PreflightReport,
    SessionDetailResponse,
    SetContextRequest,
    SetContextResponse,
    Source,
    rule_engine_from_dict,
    sources_from_chunks,
    sources_to_json,
)
from app.services.ai_review import run_ai_review
from app.services.context_extractor import SessionContext, apply_context_to_report
from app.schemas.agent import (
    AckCommandRequest,
    BatchApplyRequest,
    BatchOut,
    CommandOut,
    EnqueueCommandRequest,
    command_to_out,
)
from app.services import agent_ops
from app.services.agent_ops import OpValidationError
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
    ip = getattr(request.state, "client_ip", None)
    if not svg_file.filename or not svg_file.filename.lower().endswith(".svg"):
        analytics.record_event(
            "upload_rejected", ip=ip,
            meta={"stage": "create", "reason": "invalid_extension", "filename": svg_file.filename},
        )
        raise HTTPException(status_code=400, detail="Upload must be an .svg file.")

    raw = await svg_file.read()
    if len(raw) > settings.MAX_SVG_BYTES:
        analytics.record_event(
            "upload_rejected", ip=ip,
            meta={"stage": "create", "reason": "too_large", "filename": svg_file.filename, "bytes": len(raw)},
        )
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


@router.post("/{session_id}/context", response_model=SetContextResponse)
async def set_session_context(session_id: str, body: SetContextRequest) -> SetContextResponse:
    """Set fabric/garment/hoop context, re-run analysis, and persist.

    Fabric-aware auto-fix values depend on this. Mirrors the context path in
    chat_service.generate_chat_reply, but from an explicit structured input.
    """
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    design_report = json.loads(row.design_report_json)
    # Preserve any existing AI findings — re-running the rules for a fabric change must not
    # wipe the LLM review's 🟡/🔵 findings.
    prior_ai = [
        issue
        for issue in ((design_report.get("cached_rule_engine") or {}).get("issues") or [])
        if isinstance(issue, dict) and issue.get("source") == "ai"
    ]
    apply_context_to_report(
        design_report,
        SessionContext(
            fabric_type=body.fabric_type,
            garment_type=body.garment_type,
            hoop_size_mm=body.hoop_size_mm,
        ),
    )
    # An explicit pick always wins: apply_context_to_report keeps an already-set physical
    # fabric, but the picker is authoritative — force it so presets/rules use the new value.
    if body.fabric_type:
        design_report.setdefault("physical", {})["fabric_type"] = body.fabric_type

    rules_payload = await run_in_threadpool(_build_rules_payload, design_report)
    if prior_ai:
        rules_payload["issues"] = list(rules_payload.get("issues") or []) + prior_ai
    design_report["cached_rule_engine"] = rules_payload
    await run_in_threadpool(
        database_service.update_design_report, session_id, design_report_to_json(design_report)
    )
    analytics.record_event(
        "fabric_set", session_id=session_id, meta={"fabric_type": body.fabric_type}
    )
    return SetContextResponse(
        session_context=design_report.get("session_context") or {},
        rule_engine=rule_engine_from_dict(rules_payload),
    )


@router.post("/{session_id}/ai-review", response_model=AiReviewResponse)
async def ai_review(session_id: str, request: Request) -> AiReviewResponse:
    """Run the LLM 'senior digitizer' review; merge its 🟡/🔵 findings into the report.

    Auto-triggered by the web app after upload (non-blocking). Idempotent: re-running
    replaces prior AI findings rather than stacking them.
    """
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    design_report = json.loads(row.design_report_json)
    rules_payload = design_report.get("cached_rule_engine")
    if not isinstance(rules_payload, dict) or "issues" not in rules_payload:
        rules_payload = await run_in_threadpool(_build_rules_payload, design_report)

    # Idempotent: drop any previous AI findings before adding fresh ones.
    rules_payload["issues"] = [
        issue
        for issue in (rules_payload.get("issues") or [])
        if isinstance(issue, dict) and issue.get("source") != "ai"
    ]

    svg_path = settings.DATA_DIR / "svgs" / f"{session_id}.svg"
    svg_bytes = svg_path.read_bytes() if svg_path.exists() else None
    ai_findings = await run_ai_review(design_report, rules_payload, svg_bytes)
    rules_payload["issues"] = list(rules_payload.get("issues") or []) + ai_findings

    design_report["cached_rule_engine"] = rules_payload
    await run_in_threadpool(
        database_service.update_design_report, session_id, design_report_to_json(design_report)
    )
    analytics.record_event(
        "ai_review_run",
        session_id=session_id,
        ip=getattr(request.state, "client_ip", None),
        meta={"count": len(ai_findings)},
    )
    return AiReviewResponse(
        rule_engine=rule_engine_from_dict(rules_payload),
        ai_reviewed=True,
        ai_count=len(ai_findings),
    )


@router.post("/{session_id}/rescan", response_model=SetContextResponse)
async def rescan_session(
    session_id: str, request: Request, svg_file: UploadFile = File(...)
) -> SetContextResponse:
    """Silently re-analyze the current live document (agent re-export) — the Verify loop.

    Unlike /svg this adds no welcome message and no chat noise. It merges the stored fabric
    context and preserves prior AI findings, so a Verify only updates deterministic findings.
    """
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    ip = getattr(request.state, "client_ip", None)
    if not svg_file.filename or not svg_file.filename.lower().endswith(".svg"):
        analytics.record_event(
            "upload_rejected", session_id=session_id, ip=ip,
            meta={"stage": "rescan", "reason": "invalid_extension", "filename": svg_file.filename},
        )
        raise HTTPException(status_code=400, detail="Upload must be an .svg file.")

    raw = await svg_file.read()
    if len(raw) > settings.MAX_SVG_BYTES:
        analytics.record_event(
            "upload_rejected", session_id=session_id, ip=ip,
            meta={"stage": "rescan", "reason": "too_large", "filename": svg_file.filename, "bytes": len(raw)},
        )
        raise HTTPException(status_code=413, detail=f"SVG exceeds {settings.MAX_SVG_BYTES} bytes.")

    old_report = json.loads(row.design_report_json)
    stored_ctx = SessionContext.from_dict(old_report.get("session_context"))
    prior_ai = [
        issue
        for issue in ((old_report.get("cached_rule_engine") or {}).get("issues") or [])
        if isinstance(issue, dict) and issue.get("source") == "ai"
    ]
    doc_name = (old_report.get("summary") or {}).get("document_name") or svg_file.filename

    svg_path = settings.DATA_DIR / "svgs" / f"{session_id}.svg"
    await run_in_threadpool(svg_path.write_bytes, raw)

    def _reanalyze() -> tuple[dict, dict]:
        report = build_design_report(raw, document_name=doc_name)
        apply_context_to_report(report, stored_ctx)
        if stored_ctx.fabric_type:
            report.setdefault("physical", {})["fabric_type"] = stored_ctx.fabric_type
        payload = _build_rules_payload(report)
        if prior_ai:
            payload["issues"] = list(payload.get("issues") or []) + prior_ai
        report["cached_rule_engine"] = payload
        return report, payload

    design_report, rules_payload = await run_in_threadpool(_reanalyze)
    await run_in_threadpool(
        database_service.update_design_report, session_id, design_report_to_json(design_report)
    )
    analytics.record_event("rescan", session_id=session_id, ip=ip)
    return SetContextResponse(
        session_context=design_report.get("session_context") or {},
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

    ip = getattr(request.state, "client_ip", None)
    if not svg_file.filename or not svg_file.filename.lower().endswith(".svg"):
        analytics.record_event(
            "upload_rejected", session_id=session_id, ip=ip,
            meta={"stage": "replace", "reason": "invalid_extension", "filename": svg_file.filename},
        )
        raise HTTPException(status_code=400, detail="Upload must be an .svg file.")

    raw = await svg_file.read()
    if len(raw) > settings.MAX_SVG_BYTES:
        analytics.record_event(
            "upload_rejected", session_id=session_id, ip=ip,
            meta={"stage": "replace", "reason": "too_large", "filename": svg_file.filename, "bytes": len(raw)},
        )
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
    if welcome_content:
        await run_in_threadpool(
            database_service.add_message, session_id, "assistant", welcome_content, "[]"
        )
    logger.info("session_svg_uploaded", session_id=session_id, filename=svg_file.filename)

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


# --------------------------------------------------------------------------- #
# Agent command queue + AI action history
#
# The web app enqueues commands; the local agent polls /pending, executes them via
# Inkscape actions, and posts /ack with results and before-values. The session id in
# the path is the capability token — there is no inbound listener on the user's machine.
# --------------------------------------------------------------------------- #


def _require_session(session_id: str):
    row = database_service.get_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return row


def _summarize_batches(rows: list) -> list[BatchOut]:
    groups: dict[str, list] = {}
    for cmd in rows:
        if cmd.batch_id:
            groups.setdefault(cmd.batch_id, []).append(cmd)
    out: list[BatchOut] = []
    for batch_id, cmds in groups.items():
        cmds.sort(key=lambda c: c.created_at)
        kind = cmds[0].kind
        revertable = kind != "revert" and any(
            c.kind == "apply" and c.status == "done" and c.before_json for c in cmds
        )
        out.append(
            BatchOut(
                batch_id=batch_id,
                kind=kind,
                total=len(cmds),
                done=sum(1 for c in cmds if c.status == "done"),
                failed=sum(1 for c in cmds if c.status == "failed"),
                pending=sum(1 for c in cmds if c.status == "pending"),
                revertable=revertable,
                created_at=cmds[0].created_at,
            )
        )
    out.sort(key=lambda b: b.created_at, reverse=True)
    return out


@router.post("/{session_id}/commands", response_model=CommandOut)
async def enqueue_command(session_id: str, body: EnqueueCommandRequest) -> CommandOut:
    _require_session(session_id)
    try:
        agent_ops.validate_command(body.kind, body.payload)
    except OpValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    cmds = await run_in_threadpool(
        database_service.enqueue_commands,
        session_id,
        [{"kind": body.kind, "issue_id": body.issue_id, "payload": body.payload}],
        None,
    )
    return command_to_out(cmds[0])


@router.post("/{session_id}/commands/batch", response_model=list[CommandOut])
async def enqueue_command_batch(session_id: str, body: BatchApplyRequest) -> list[CommandOut]:
    """Enqueue many 🟢 fixes as one named batch (for 'Fix all 🟢' + Revert Batch)."""
    _require_session(session_id)
    if not body.fixes:
        raise HTTPException(status_code=400, detail="No fixes provided.")
    try:
        for item in body.fixes:
            agent_ops.validate_apply_payload(item.payload)
    except OpValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    batch_id = str(uuid.uuid4())
    items = [{"kind": "apply", "issue_id": f.issue_id, "payload": f.payload} for f in body.fixes]
    cmds = await run_in_threadpool(database_service.enqueue_commands, session_id, items, batch_id)
    return [command_to_out(c) for c in cmds]


@router.get("/{session_id}/commands/pending", response_model=list[CommandOut])
async def poll_commands(session_id: str) -> list[CommandOut]:
    """Agent poll: pending commands, oldest first."""
    _require_session(session_id)
    cmds = await run_in_threadpool(database_service.pending_commands, session_id)
    return [command_to_out(c) for c in cmds]


@router.post("/{session_id}/commands/{command_id}/ack", response_model=CommandOut)
async def ack_command(session_id: str, command_id: str, body: AckCommandRequest) -> CommandOut:
    """Agent ack: report done/failed + before-values (for revert) + result."""
    cmd = database_service.get_command(command_id)
    if not cmd or cmd.session_id != session_id:
        raise HTTPException(status_code=404, detail="Command not found.")
    if body.status not in ("done", "failed"):
        raise HTTPException(status_code=400, detail="status must be 'done' or 'failed'.")
    updated = await run_in_threadpool(
        database_service.ack_command, command_id, body.status, body.before, body.result
    )
    # Funnel signal: a successfully applied fix is the clearest sign of automation appetite.
    if cmd.kind == "apply" and body.status == "done":
        analytics.record_event(
            "fix_applied", session_id=session_id, meta={"issue_id": cmd.issue_id}
        )
    return command_to_out(updated)


@router.get("/{session_id}/commands/{command_id}", response_model=CommandOut)
async def get_command(session_id: str, command_id: str) -> CommandOut:
    """Fetch one command's status/result (web UI polls this after Apply)."""
    cmd = database_service.get_command(command_id)
    if not cmd or cmd.session_id != session_id:
        raise HTTPException(status_code=404, detail="Command not found.")
    return command_to_out(cmd)


@router.post("/{session_id}/commands/{command_id}/revert", response_model=list[CommandOut])
async def revert_command(session_id: str, command_id: str) -> list[CommandOut]:
    """Undo a single applied fix by enqueueing its inverse (restores before-values)."""
    cmd = database_service.get_command(command_id)
    if not cmd or cmd.session_id != session_id:
        raise HTTPException(status_code=404, detail="Command not found.")
    items = agent_ops.inverse_items([cmd])
    if not items:
        raise HTTPException(status_code=400, detail="This fix cannot be undone.")
    created = await run_in_threadpool(database_service.enqueue_commands, session_id, items, None)
    # Funnel signal: mirrors the "fix_applied" event in ack_command, but for undo.
    analytics.record_event(
        "fix_reverted", session_id=session_id, meta={"issue_id": cmd.issue_id}
    )
    return [command_to_out(c) for c in created]


@router.get("/{session_id}/batches", response_model=list[BatchOut])
async def list_batches(session_id: str) -> list[BatchOut]:
    """AI action history: batches, newest first, with revert availability."""
    _require_session(session_id)
    rows = await run_in_threadpool(database_service.list_batches, session_id)
    return _summarize_batches(rows)


@router.post("/{session_id}/batches/{batch_id}/revert", response_model=list[CommandOut])
async def revert_batch(session_id: str, batch_id: str) -> list[CommandOut]:
    """Revert a whole AI batch by enqueueing synthesized inverse ops as a new batch."""
    _require_session(session_id)
    cmds = await run_in_threadpool(database_service.batch_commands, session_id, batch_id)
    if not cmds:
        raise HTTPException(status_code=404, detail="Batch not found.")
    items = agent_ops.inverse_items(cmds)
    if not items:
        raise HTTPException(status_code=400, detail="Nothing in this batch can be reverted.")
    new_batch = str(uuid.uuid4())
    created = await run_in_threadpool(database_service.enqueue_commands, session_id, items, new_batch)
    analytics.record_event(
        "fix_reverted", session_id=session_id, meta={"batch_id": batch_id, "count": len(items)}
    )
    return [command_to_out(c) for c in created]
