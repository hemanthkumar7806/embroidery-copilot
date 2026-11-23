"""Request/response schemas for the agent command queue + AI action history."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class EnqueueCommandRequest(BaseModel):
    kind: str  # apply | highlight | verify | revert
    issue_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class BatchApplyItem(BaseModel):
    issue_id: str | None = None
    payload: dict[str, Any]


class BatchApplyRequest(BaseModel):
    """Apply many 🟢 fixes as one named batch (e.g. 'Fix all 🟢')."""

    fixes: list[BatchApplyItem]


class AckCommandRequest(BaseModel):
    status: str  # done | failed
    # Generic before-values captured by the agent: {target_id: {attribute, old}}.
    before: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class CommandOut(BaseModel):
    id: str
    session_id: str
    batch_id: str | None = None
    kind: str
    issue_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str
    result: dict[str, Any] | None = None
    created_at: datetime


class BatchOut(BaseModel):
    batch_id: str
    kind: str
    total: int
    done: int
    failed: int
    pending: int
    revertable: bool
    created_at: datetime


def _loads(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def command_to_out(cmd: Any) -> CommandOut:
    # SQLite drops tzinfo on round-trip - created_at is UTC by convention
    # (see AgentCommand's default factory), so re-attach it before Pydantic
    # serializes it, or the admin UI misreads it as local time.
    created_at = cmd.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return CommandOut(
        id=cmd.id,
        session_id=cmd.session_id,
        batch_id=cmd.batch_id,
        kind=cmd.kind,
        issue_id=cmd.issue_id,
        payload=_loads(cmd.payload_json) or {},
        status=cmd.status,
        result=_loads(cmd.result_json),
        created_at=created_at,
    )
