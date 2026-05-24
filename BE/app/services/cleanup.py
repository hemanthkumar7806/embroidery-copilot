"""TTL cleanup for anonymous beta sessions."""

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.logging import logger
from app.services.database import database_service


def cleanup_expired_sessions() -> None:
    expired = database_service.list_expired_sessions()
    removed = 0
    for session in expired:
        if database_service.delete_session(session.id):
            removed += 1
    if removed:
        logger.info("sessions_cleaned_up", count=removed)


def start_cleanup_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_sessions, "interval", hours=1, id="session_cleanup")
    scheduler.start()
    logger.info("cleanup_scheduler_started")
    return scheduler
