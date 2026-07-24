"""Persistent user-journey analytics tables.

These are intentionally separate from the operational `session`/`message`
tables so the TTL cleanup never removes them. They capture the anonymous
end-to-end journey (visitors, sessions, SVGs, chats, timings, findings, errors)
for validating the product with real usage.
"""

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AnalyticsVisitor(SQLModel, table=True):
    """One anonymous visitor, identified by a persistent browser cookie."""

    __tablename__ = "analytics_visitor"

    id: str = Field(primary_key=True)
    first_seen_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow)
    first_ip: Optional[str] = None
    last_ip: Optional[str] = None
    user_agent: Optional[str] = None
    first_referrer: Optional[str] = None
    session_count: int = 0
    message_count: int = 0


class AnalyticsSession(SQLModel, table=True):
    """One review/chat session; mirrors the operational session but persists."""

    __tablename__ = "analytics_session"

    id: str = Field(primary_key=True)
    visitor_id: Optional[str] = Field(default=None, index=True)
    kind: str = "svg"  # svg | chat_only
    source: Optional[str] = None  # e.g. inkscape | web
    filename: Optional[str] = None
    svg_bytes: Optional[int] = None
    svg_width_mm: Optional[float] = None
    svg_height_mm: Optional[float] = None
    element_count: Optional[int] = None
    svg_text: Optional[str] = None
    rule_status: Optional[str] = None
    issue_count: Optional[int] = None
    top_issues_json: Optional[str] = None
    process_ms: Optional[int] = None
    total_ms: Optional[int] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow, index=True)
    opened_at: Optional[datetime] = None
    message_count: int = 0


class AnalyticsMessage(SQLModel, table=True):
    """One chat turn (user or assistant), kept permanently for the journey."""

    __tablename__ = "analytics_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    visitor_id: Optional[str] = Field(default=None, index=True)
    role: str
    content: str
    latency_ms: Optional[int] = None
    rag_status: Optional[str] = None
    rag_chunk_count: Optional[int] = None
    created_at: datetime = Field(default_factory=_utcnow, index=True)


class AnalyticsEvent(SQLModel, table=True):
    """Flexible journey milestone log (created, opened, replaced, error, ...)."""

    __tablename__ = "analytics_event"

    id: Optional[int] = Field(default=None, primary_key=True)
    visitor_id: Optional[str] = Field(default=None, index=True)
    session_id: Optional[str] = Field(default=None, index=True)
    event_type: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow, index=True)
    ip: Optional[str] = None
    meta_json: Optional[str] = None
