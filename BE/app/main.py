"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import logger
from app.core.middleware import (
    AdminCORSMiddleware,
    LoggingContextMiddleware,
    VisitorContextMiddleware,
)
from app.services.cleanup import start_cleanup_scheduler
from app.services.database import database_service
from app.services.rag import rag_service

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    database_service.init_db()
    _scheduler = start_cleanup_scheduler()
    logger.info("application_startup", project=settings.PROJECT_NAME, version=settings.VERSION)
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(LoggingContextMiddleware)
app.add_middleware(VisitorContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Added last => outermost, so it handles the admin preflight before the strict
# CORSMiddleware can reject the standalone dashboard's origin.
app.add_middleware(AdminCORSMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("validation_error", path=request.url.path, errors=str(exc.errors()))
    formatted = [
        {"field": " -> ".join(str(part) for part in err["loc"] if part != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": formatted},
    )


app.include_router(api_router, prefix=settings.API_V1_STR)

# Analytics admin API. Mounted before the "/" static mount so the
# prefix is matched first. No auth (see app/api/v1/admin.py) — don't share this URL.
from app.api.v1.admin import admin_app  # noqa: E402

app.mount("/admin/api", admin_app)


_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_STATIC_INDEX = _STATIC_DIR / "index.html"


@app.get("/health")
async def health_check() -> dict[str, Any]:
    db_ok = database_service.health_check()
    cfg_status, cfg_detail = rag_service.config_status()
    rag_component = "ready" if cfg_status == "ok" and settings.has_rag else cfg_status
    payload = {
        "status": "healthy" if db_ok else "degraded",
        "version": settings.VERSION,
        "components": {
            "api": "healthy",
            "database": "healthy" if db_ok else "unhealthy",
            "rag": rag_component,
        },
        "rag_detail": cfg_detail or None,
        "timestamp": datetime.now().isoformat(),
    }
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=code)


if _STATIC_INDEX.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="ui")