"""Private admin API for the analytics dashboard.

Mounted as a standalone sub-application with permissive CORS so the standalone
admin/index.html (opened from the file system) can call it with an
``X-Admin-Token`` header. Access requires ``settings.ADMIN_TOKEN`` to be set;
when it is empty the admin API is disabled.
"""

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.services import analytics


async def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if not settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API disabled: set ADMIN_TOKEN in the backend environment.",
        )
    if not x_admin_token or x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token.",
        )


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
    """Unauthenticated reachability check that also reports if admin is enabled."""
    return {"ok": True, "admin_enabled": bool(settings.ADMIN_TOKEN)}


@admin_app.get("/overview", dependencies=[Depends(require_admin)])
async def get_overview() -> dict:
    return await run_in_threadpool(analytics.overview)


@admin_app.get("/visitors", dependencies=[Depends(require_admin)])
async def get_visitors(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    rows = await run_in_threadpool(analytics.list_visitors, limit, offset)
    return {"visitors": rows}


@admin_app.get("/sessions", dependencies=[Depends(require_admin)])
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


@admin_app.get("/sessions/{session_id}", dependencies=[Depends(require_admin)])
async def get_session_detail(session_id: str) -> dict:
    detail = await run_in_threadpool(analytics.session_detail, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return detail


@admin_app.get("/events", dependencies=[Depends(require_admin)])
async def get_events(limit: int = Query(200, ge=1, le=1000)) -> dict:
    rows = await run_in_threadpool(analytics.recent_events, limit)
    return {"events": rows}
