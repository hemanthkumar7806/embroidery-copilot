"""Request middleware: structured-log context and anonymous visitor tracking."""

import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from app.core.config import settings
from app.core.logging import bind_context, clear_context

_ADMIN_PREFIX = "/admin/api"


class AdminCORSMiddleware(BaseHTTPMiddleware):
    """Permissive, token-agnostic CORS for the admin API only.

    Must be the OUTERMOST middleware so it handles the admin preflight before
    the app's strict CORSMiddleware (which would otherwise reject the standalone
    dashboard's origin, including the ``null`` origin of a file:// page). The
    admin API has no auth and uses no cookies, so a wildcard origin without
    credentials is safe here — but note the API itself is unauthenticated.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        is_admin = request.url.path.startswith(_ADMIN_PREFIX)
        if is_admin and request.method == "OPTIONS":
            req_headers = request.headers.get("access-control-request-headers", "*")
            return PlainTextResponse(
                "",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": req_headers,
                    "Access-Control-Max-Age": "600",
                    "Vary": "Origin",
                },
            )
        response = await call_next(request)
        if is_admin:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Vary"] = "Origin"
        return response

# ~2 years so a beta tester's journey persists across visits.
_COOKIE_MAX_AGE = 60 * 60 * 24 * 730


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id to structured logs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            clear_context()
            bind_context(request_id=str(uuid.uuid4()))
            return await call_next(request)
        finally:
            clear_context()


def _client_ip(request: Request) -> str | None:
    """Real client IP, honoring the X-Forwarded-For set by the Caddy proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else None


class VisitorContextMiddleware(BaseHTTPMiddleware):
    """Read or mint a persistent anonymous visitor id and expose request context.

    Sets request.state.visitor_id / client_ip / user_agent / referrer for
    endpoints to record analytics, and (re)sets the visitor cookie on the way
    out so the same browser is recognized on later visits.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cookie_name = settings.VISITOR_COOKIE_NAME
        visitor_id = request.cookies.get(cookie_name)
        is_new = False
        if not visitor_id:
            visitor_id = str(uuid.uuid4())
            is_new = True

        request.state.visitor_id = visitor_id
        request.state.visitor_is_new = is_new
        request.state.client_ip = _client_ip(request)
        request.state.user_agent = request.headers.get("user-agent")
        request.state.referrer = request.headers.get("referer")

        response = await call_next(request)

        # Refresh the cookie so its expiry keeps sliding forward.
        response.set_cookie(
            key=cookie_name,
            value=visitor_id,
            max_age=_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=settings.COOKIE_SECURE,
            path="/",
        )
        return response
