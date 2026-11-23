"""Fail-safe recorders and admin queries for user-journey analytics.

All write paths swallow errors (and log them) so analytics can never break a
user-facing request. Read paths are used only by the token-protected admin API.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import desc, func
from sqlmodel import Session as DBSession
from sqlmodel import select

from app.core.config import settings
from app.core.logging import logger
from app.models.analytics import (
    AnalyticsEvent,
    AnalyticsMessage,
    AnalyticsSession,
    AnalyticsVisitor,
)
from app.services.database import database_service


def _now() -> datetime:
    return datetime.now(UTC)


def _enabled() -> bool:
    return settings.ANALYTICS_ENABLED


def summarize_rules(rules_payload: dict | None, top_n: int = 100) -> tuple[Optional[str], int, list[dict]]:
    """Extract (rule_status, issue_count, top_issues) from a rule-engine payload.

    top_n is generous (not really "top" N) so the admin replay view can
    reconstruct the full findings panel the user actually saw, not just a
    5-item summary. capability is included so it can be grouped into the
    same auto_fix/guided/recommendation tiers as the real UI.
    """
    if not rules_payload:
        return None, 0, []
    decision = rules_payload.get("decision") or {}
    status = decision.get("status")
    issues = rules_payload.get("issues") or []
    top = [
        {
            "id": i.get("id", ""),
            "title": i.get("title", ""),
            "severity": i.get("severity", ""),
            "category": i.get("category", ""),
            "capability": i.get("capability", "recommendation"),
            "detail": i.get("detail", ""),
        }
        for i in issues[:top_n]
    ]
    return status, len(issues), top


# --------------------------------------------------------------------------- #
# Write paths (fail-safe)
# --------------------------------------------------------------------------- #

def get_or_create_visitor(
    visitor_id: Optional[str],
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    referrer: Optional[str] = None,
) -> None:
    if not _enabled() or not visitor_id:
        return
    try:
        with DBSession(database_service.engine) as db:
            row = db.get(AnalyticsVisitor, visitor_id)
            now = _now()
            if row is None:
                db.add(
                    AnalyticsVisitor(
                        id=visitor_id,
                        first_seen_at=now,
                        last_seen_at=now,
                        first_ip=ip,
                        last_ip=ip,
                        user_agent=user_agent,
                        first_referrer=referrer,
                    )
                )
            else:
                row.last_seen_at = now
                if ip:
                    row.last_ip = ip
                if user_agent and not row.user_agent:
                    row.user_agent = user_agent
                db.add(row)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_visitor_failed", error=str(exc))


def record_session(
    *,
    session_id: str,
    kind: str,
    source: Optional[str] = None,
    filename: Optional[str] = None,
    svg_bytes: Optional[int] = None,
    svg_width_mm: Optional[float] = None,
    svg_height_mm: Optional[float] = None,
    element_count: Optional[int] = None,
    svg_text: Optional[str] = None,
    rule_status: Optional[str] = None,
    issue_count: Optional[int] = None,
    top_issues: Optional[list[dict]] = None,
    process_ms: Optional[int] = None,
    total_ms: Optional[int] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    visitor_id: Optional[str] = None,
) -> None:
    if not _enabled():
        return
    try:
        with DBSession(database_service.engine) as db:
            db.add(
                AnalyticsSession(
                    id=session_id,
                    visitor_id=visitor_id,
                    kind=kind,
                    source=source,
                    filename=filename,
                    svg_bytes=svg_bytes,
                    svg_width_mm=svg_width_mm,
                    svg_height_mm=svg_height_mm,
                    element_count=element_count,
                    svg_text=svg_text,
                    rule_status=rule_status,
                    issue_count=issue_count,
                    top_issues_json=json.dumps(top_issues or []),
                    process_ms=process_ms,
                    total_ms=total_ms,
                    ip=ip,
                    user_agent=user_agent,
                )
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_session_failed", error=str(exc))


def update_session_svg(
    *,
    session_id: str,
    filename: Optional[str],
    svg_bytes: Optional[int],
    svg_width_mm: Optional[float],
    svg_height_mm: Optional[float],
    element_count: Optional[int],
    svg_text: Optional[str],
    rule_status: Optional[str],
    issue_count: Optional[int],
    top_issues: Optional[list[dict]],
) -> None:
    if not _enabled():
        return
    try:
        with DBSession(database_service.engine) as db:
            row = db.get(AnalyticsSession, session_id)
            if not row:
                return
            row.filename = filename or row.filename
            row.svg_bytes = svg_bytes
            row.svg_width_mm = svg_width_mm
            row.svg_height_mm = svg_height_mm
            row.element_count = element_count
            row.svg_text = svg_text
            row.rule_status = rule_status
            row.issue_count = issue_count
            row.top_issues_json = json.dumps(top_issues or [])
            db.add(row)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_session_update_failed", error=str(exc))


def update_session_issues(
    session_id: str,
    rule_status: Optional[str],
    issue_count: Optional[int],
    top_issues: Optional[list[dict]],
) -> None:
    """Refresh just the issue/verdict fields after AI review adds findings.

    Deliberately narrower than update_session_svg - that one overwrites the SVG
    snapshot (bytes/dimensions/text) unconditionally, which would wipe the admin
    preview if called here without re-supplying them. AI review only changes the
    findings, not the file, so only the findings should move.
    """
    if not _enabled():
        return
    try:
        with DBSession(database_service.engine) as db:
            row = db.get(AnalyticsSession, session_id)
            if not row:
                return
            row.rule_status = rule_status
            row.issue_count = issue_count
            row.top_issues_json = json.dumps(top_issues or [])
            db.add(row)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_session_issues_update_failed", error=str(exc))


def link_visitor_to_session(
    session_id: str,
    visitor_id: Optional[str],
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """On the first browser touch, attach the visitor to the session."""
    if not _enabled() or not visitor_id:
        return
    try:
        with DBSession(database_service.engine) as db:
            row = db.get(AnalyticsSession, session_id)
            if not row:
                return
            newly_linked = row.visitor_id is None
            if newly_linked:
                row.visitor_id = visitor_id
            if row.opened_at is None:
                row.opened_at = _now()
            if ip and not row.ip:
                row.ip = ip
            if user_agent and not row.user_agent:
                row.user_agent = user_agent
            db.add(row)
            if newly_linked:
                visitor = db.get(AnalyticsVisitor, visitor_id)
                if visitor:
                    visitor.session_count = (visitor.session_count or 0) + 1
                    db.add(visitor)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_link_failed", error=str(exc))


def record_message(
    *,
    session_id: str,
    visitor_id: Optional[str],
    role: str,
    content: str,
    latency_ms: Optional[int] = None,
    rag_status: Optional[str] = None,
    rag_chunk_count: Optional[int] = None,
) -> None:
    if not _enabled():
        return
    try:
        with DBSession(database_service.engine) as db:
            db.add(
                AnalyticsMessage(
                    session_id=session_id,
                    visitor_id=visitor_id,
                    role=role,
                    content=content,
                    latency_ms=latency_ms,
                    rag_status=rag_status,
                    rag_chunk_count=rag_chunk_count,
                )
            )
            sess = db.get(AnalyticsSession, session_id)
            if sess:
                sess.message_count = (sess.message_count or 0) + 1
                db.add(sess)
            if visitor_id:
                visitor = db.get(AnalyticsVisitor, visitor_id)
                if visitor:
                    visitor.message_count = (visitor.message_count or 0) + 1
                    db.add(visitor)
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_message_failed", error=str(exc))


def record_event(
    event_type: str,
    *,
    visitor_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip: Optional[str] = None,
    meta: Optional[dict] = None,
) -> None:
    if not _enabled():
        return
    try:
        with DBSession(database_service.engine) as db:
            db.add(
                AnalyticsEvent(
                    event_type=event_type,
                    visitor_id=visitor_id,
                    session_id=session_id,
                    ip=ip,
                    meta_json=json.dumps(meta) if meta else None,
                )
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_event_failed", error=str(exc))


# --------------------------------------------------------------------------- #
# Read paths (admin dashboard)
# --------------------------------------------------------------------------- #

def _count(db: DBSession, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for cond in where:
        stmt = stmt.where(cond)
    return int(db.exec(stmt).one())


def overview() -> dict[str, Any]:
    now = _now()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    with DBSession(database_service.engine) as db:
        visitors = _count(db, AnalyticsVisitor)
        sessions = _count(db, AnalyticsSession)
        messages = _count(db, AnalyticsMessage)
        sessions_24h = _count(db, AnalyticsSession, AnalyticsSession.created_at >= day_ago)
        sessions_7d = _count(db, AnalyticsSession, AnalyticsSession.created_at >= week_ago)
        user_messages = _count(db, AnalyticsMessage, AnalyticsMessage.role == "user")

        avg_latency = db.exec(
            select(func.avg(AnalyticsMessage.latency_ms)).where(
                AnalyticsMessage.role == "assistant",
                AnalyticsMessage.latency_ms.is_not(None),
            )
        ).one()
        avg_latency_ms = int(avg_latency) if avg_latency is not None else None

        status_rows = db.exec(
            select(AnalyticsSession.rule_status, func.count())
            .group_by(AnalyticsSession.rule_status)
        ).all()
        rule_status_distribution = {
            (status or "unknown"): int(cnt) for status, cnt in status_rows
        }

        kind_rows = db.exec(
            select(AnalyticsSession.kind, func.count()).group_by(AnalyticsSession.kind)
        ).all()
        session_kind_distribution = {(k or "unknown"): int(c) for k, c in kind_rows}

        # Sessions over the last 14 days, bucketed in Python for cross-db safety.
        recent = db.exec(
            select(AnalyticsSession.created_at).where(
                AnalyticsSession.created_at >= now - timedelta(days=14)
            )
        ).all()
        day_counts: Counter[str] = Counter()
        for created in recent:
            if created is not None:
                day_counts[created.date().isoformat()] += 1
        sessions_over_time = [
            {"date": d, "count": day_counts.get(d, 0)}
            for d in _last_n_days(14)
        ]

        # Top issues aggregated from stored per-session summaries.
        issue_rows = db.exec(select(AnalyticsSession.top_issues_json)).all()
        issue_counter: Counter[str] = Counter()
        for raw in issue_rows:
            if not raw:
                continue
            try:
                for issue in json.loads(raw):
                    title = issue.get("title") or issue.get("id")
                    if title:
                        issue_counter[title] += 1
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
        top_issues = [
            {"title": title, "count": count}
            for title, count in issue_counter.most_common(10)
        ]

    avg_msgs = round(messages / sessions, 2) if sessions else 0
    return {
        "totals": {
            "visitors": visitors,
            "sessions": sessions,
            "messages": messages,
            "user_messages": user_messages,
            "sessions_24h": sessions_24h,
            "sessions_7d": sessions_7d,
            "avg_messages_per_session": avg_msgs,
            "avg_assistant_latency_ms": avg_latency_ms,
        },
        "rule_status_distribution": rule_status_distribution,
        "session_kind_distribution": session_kind_distribution,
        "sessions_over_time": sessions_over_time,
        "top_issues": top_issues,
        "generated_at": now.isoformat(),
    }


def _last_n_days(n: int) -> list[str]:
    today = _now().date()
    return [(today - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def list_visitors(limit: int = 100, offset: int = 0) -> list[dict]:
    with DBSession(database_service.engine) as db:
        rows = db.exec(
            select(AnalyticsVisitor)
            .order_by(desc(AnalyticsVisitor.last_seen_at))
            .limit(limit)
            .offset(offset)
        ).all()
        return [_visitor_dict(v) for v in rows]


def list_sessions(
    visitor_id: Optional[str] = None,
    kind: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    with DBSession(database_service.engine) as db:
        stmt = select(AnalyticsSession).order_by(desc(AnalyticsSession.created_at))
        if visitor_id:
            stmt = stmt.where(AnalyticsSession.visitor_id == visitor_id)
        if kind:
            stmt = stmt.where(AnalyticsSession.kind == kind)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(AnalyticsSession.filename.ilike(like))
        rows = db.exec(stmt.limit(limit).offset(offset)).all()
        return [_session_dict(s, include_svg=False) for s in rows]


def session_detail(session_id: str) -> Optional[dict]:
    with DBSession(database_service.engine) as db:
        row = db.get(AnalyticsSession, session_id)
        if not row:
            return None
        messages = db.exec(
            select(AnalyticsMessage)
            .where(AnalyticsMessage.session_id == session_id)
            .order_by(AnalyticsMessage.created_at)
        ).all()
        events = db.exec(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.session_id == session_id)
            .order_by(AnalyticsEvent.created_at)
        ).all()
        detail = _session_dict(row, include_svg=True)
        detail["messages"] = [_message_dict(m) for m in messages]
        detail["events"] = [_event_dict(e) for e in events]
        return detail


def recent_events(limit: int = 200, visitor_id: Optional[str] = None) -> list[dict]:
    with DBSession(database_service.engine) as db:
        stmt = select(AnalyticsEvent).order_by(desc(AnalyticsEvent.created_at))
        if visitor_id:
            stmt = stmt.where(AnalyticsEvent.visitor_id == visitor_id)
        rows = db.exec(stmt.limit(limit)).all()
        return [_event_dict(e) for e in rows]


# --------------------------------------------------------------------------- #
# Serializers
# --------------------------------------------------------------------------- #

def _iso(dt: Optional[datetime]) -> Optional[str]:
    """ISO-8601 with an explicit UTC offset.

    SQLite has no timestamptz type, so a timezone-aware `datetime.now(UTC)`
    round-trips through it as naive (tzinfo lost) - dt.isoformat() would then
    omit the offset, and the browser's `new Date(...)` parses that as local
    time instead of UTC, silently shifting every displayed time. All stored
    timestamps are UTC by convention (see the model default factories), so
    re-attaching UTC here is always correct, not an assumption per-row.
    """
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def _visitor_dict(v: AnalyticsVisitor) -> dict:
    return {
        "id": v.id,
        "first_seen_at": _iso(v.first_seen_at),
        "last_seen_at": _iso(v.last_seen_at),
        "first_ip": v.first_ip,
        "last_ip": v.last_ip,
        "user_agent": v.user_agent,
        "first_referrer": v.first_referrer,
        "session_count": v.session_count,
        "message_count": v.message_count,
    }


def _session_dict(s: AnalyticsSession, include_svg: bool) -> dict:
    try:
        top_issues = json.loads(s.top_issues_json) if s.top_issues_json else []
    except (json.JSONDecodeError, TypeError):
        top_issues = []
    data = {
        "id": s.id,
        "visitor_id": s.visitor_id,
        "kind": s.kind,
        "source": s.source,
        "filename": s.filename,
        "svg_bytes": s.svg_bytes,
        "svg_width_mm": s.svg_width_mm,
        "svg_height_mm": s.svg_height_mm,
        "element_count": s.element_count,
        "rule_status": s.rule_status,
        "issue_count": s.issue_count,
        "top_issues": top_issues,
        "process_ms": s.process_ms,
        "total_ms": s.total_ms,
        "ip": s.ip,
        "user_agent": s.user_agent,
        "created_at": _iso(s.created_at),
        "opened_at": _iso(s.opened_at),
        "message_count": s.message_count,
    }
    if include_svg:
        data["svg_text"] = s.svg_text
    return data


def _message_dict(m: AnalyticsMessage) -> dict:
    return {
        "id": m.id,
        "session_id": m.session_id,
        "visitor_id": m.visitor_id,
        "role": m.role,
        "content": m.content,
        "latency_ms": m.latency_ms,
        "rag_status": m.rag_status,
        "rag_chunk_count": m.rag_chunk_count,
        "created_at": _iso(m.created_at),
    }


def _event_dict(e: AnalyticsEvent) -> dict:
    try:
        meta = json.loads(e.meta_json) if e.meta_json else None
    except (json.JSONDecodeError, TypeError):
        meta = None
    return {
        "id": e.id,
        "visitor_id": e.visitor_id,
        "session_id": e.session_id,
        "event_type": e.event_type,
        "created_at": _iso(e.created_at),
        "ip": e.ip,
        "meta": meta,
    }
