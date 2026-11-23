"""Private admin API for the analytics dashboard.

Mounted as a standalone sub-application with permissive CORS so the standalone
admin/index.html (opened from the file system) can call it.
"""

import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.schemas.agent import command_to_out
from app.services import analytics
from app.services.database import database_service

admin_app = FastAPI(
    title="Inkscape AI Admin API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS for the admin API is handled by AdminCORSMiddleware on the parent app
# (it must run before the parent's strict CORSMiddleware), so nothing is needed
# here.


@admin_app.get("/ping")
async def ping() -> dict:
    """Unauthenticated reachability check."""
    return {"ok": True, "admin_enabled": True}


@admin_app.get("/overview")
async def get_overview() -> dict:
    return await run_in_threadpool(analytics.overview)


@admin_app.get("/visitors")
async def get_visitors(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    rows = await run_in_threadpool(analytics.list_visitors, limit, offset)
    return {"visitors": rows}


@admin_app.get("/sessions")
async def get_sessions(
    visitor_id: Optional[str] = None,
    kind: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    rows = await run_in_threadpool(
        analytics.list_sessions, visitor_id, kind, q, limit, offset
    )
    return {"sessions": rows}


@admin_app.get("/sessions/{session_id}")
async def get_session_detail(session_id: str) -> dict:
    detail = await run_in_threadpool(analytics.session_detail, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # session_context (fabric/garment/symptom) lives only on the live
    # operational session, not the permanent analytics tables - so it's only
    # available while the session is still within its TTL window.
    live = await run_in_threadpool(database_service.get_session, session_id)
    if live is not None:
        try:
            report = json.loads(live.design_report_json or "{}")
        except (json.JSONDecodeError, TypeError):
            report = {}
        detail["session_context"] = report.get("session_context")

    return detail


@admin_app.get("/sessions/{session_id}/actions")
async def get_session_actions(session_id: str) -> dict:
    """Every Fix/Undo/Verify/Highlight the user clicked in this session -
    the operational agentcommand queue, not the permanent analytics tables
    (so this only covers sessions still within the TTL window).
    """
    cmds = await run_in_threadpool(database_service.list_commands, session_id)
    return {"actions": [command_to_out(c) for c in cmds]}


@admin_app.get("/events")
async def get_events(
    limit: int = Query(200, ge=1, le=1000),
    visitor_id: Optional[str] = None,
) -> dict:
    rows = await run_in_threadpool(analytics.recent_events, limit, visitor_id)
    return {"events": rows}
