"""SQLite database service for anonymous sessions."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import event
from sqlmodel import Session as DBSession
from sqlmodel import SQLModel, create_engine, select

from app.core.config import settings
from app.core.logging import logger
from app.models.session import Message, Session


class DatabaseService:
    """Lightweight SQLite persistence for beta sessions."""

    def __init__(self) -> None:
        db_url = f"sqlite:///{settings.sqlite_path.as_posix()}"
        # timeout => SQLite busy timeout so concurrent writers wait instead of erroring.
        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record) -> None:  # noqa: ANN001
            # WAL lets reads and writes happen concurrently (single Render worker,
            # browser + extension hitting the DB at once).
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.close()

        SQLModel.metadata.create_all(self.engine)
        logger.info("database_initialized", path=str(settings.sqlite_path))

    def init_db(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    def health_check(self) -> bool:
        try:
            with DBSession(self.engine) as session:
                session.exec(select(1)).first()
            return True
        except Exception as exc:
            logger.error("database_health_check_failed", error=str(exc))
            return False

    def create_session(
        self,
        session_id: str,
        svg_path: str,
        design_report_json: str,
        preflight_json: str,
        preflight_content: str,
    ) -> Session:
        now = datetime.now(UTC)
        with DBSession(self.engine) as db:
            row = Session(
                id=session_id,
                svg_path=svg_path,
                design_report_json=design_report_json,
                preflight_json=preflight_json,
                created_at=now,
                last_active_at=now,
            )
            db.add(row)
            db.add(
                Message(
                    session_id=session_id,
                    role="assistant",
                    content=preflight_content,
                    sources_json=preflight_json,
                )
            )
            db.commit()
            db.refresh(row)
            return row

    def get_session(self, session_id: str) -> Optional[Session]:
        with DBSession(self.engine) as db:
            return db.get(Session, session_id)

    def touch_session(self, session_id: str) -> None:
        with DBSession(self.engine) as db:
            row = db.get(Session, session_id)
            if row:
                row.last_active_at = datetime.now(UTC)
                db.add(row)
                db.commit()

    def update_design_report(self, session_id: str, design_report_json: str) -> None:
        with DBSession(self.engine) as db:
            row = db.get(Session, session_id)
            if not row:
                return
            row.design_report_json = design_report_json
            row.last_active_at = datetime.now(UTC)
            db.add(row)
            db.commit()

    def get_messages(self, session_id: str) -> list[Message]:
        with DBSession(self.engine) as db:
            stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
            return list(db.exec(stmt).all())

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources_json: Optional[str] = None,
    ) -> Message:
        with DBSession(self.engine) as db:
            msg = Message(
                session_id=session_id,
                role=role,
                content=content,
                sources_json=sources_json,
            )
            db.add(msg)
            row = db.get(Session, session_id)
            if row:
                row.last_active_at = datetime.now(UTC)
                db.add(row)
            db.commit()
            db.refresh(msg)
            return msg

    def delete_session(self, session_id: str) -> bool:
        with DBSession(self.engine) as db:
            row = db.get(Session, session_id)
            if not row:
                return False
            messages = db.exec(select(Message).where(Message.session_id == session_id)).all()
            for msg in messages:
                db.delete(msg)
            svg_path = Path(row.svg_path)
            db.delete(row)
            db.commit()
        if svg_path.exists():
            svg_path.unlink(missing_ok=True)
        return True

    def list_expired_sessions(self) -> list[Session]:
        cutoff = datetime.now(UTC) - timedelta(days=settings.SESSION_TTL_DAYS)
        with DBSession(self.engine) as db:
            stmt = select(Session).where(Session.last_active_at < cutoff)
            return list(db.exec(stmt).all())


database_service = DatabaseService()
