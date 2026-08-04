"""Private admin API for the analytics dashboard.

Mounted as a standalone sub-application with permissive CORS so the standalone
admin/index.html (opened from the file system) can call it.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.services import analytics

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
    return detail


@admin_app.get("/events")
async def get_events(limit: int = Query(200, ge=1, le=1000)) -> dict:
    rows = await run_in_threadpool(analytics.recent_events, limit)
    return {"events": rows}
