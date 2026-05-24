"""Session and message models for anonymous beta sessions."""

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    """Anonymous review session tied to one uploaded SVG."""

    id: str = Field(primary_key=True)
    svg_path: str
    design_report_json: str = Field(default="{}")
    preflight_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Message(SQLModel, table=True):
    """Chat message within a session."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    role: str
    content: str
    sources_json: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
