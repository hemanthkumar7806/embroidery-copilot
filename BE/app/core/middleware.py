"""Request logging middleware."""

import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import bind_context, clear_context


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id to structured logs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            clear_context()
            bind_context(request_id=str(uuid.uuid4()))
            return await call_next(request)
        finally:
            clear_context()
