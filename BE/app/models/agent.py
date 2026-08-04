"""Agent command queue + AI action history for live in-Inkscape fixes.

The web app enqueues commands (apply / highlight / verify / revert); the local agent
polls pending commands, executes them via Inkscape actions, and acks with results.
Applied 🟢 fixes record their before-values so a whole batch can be reverted in one
action ("Revert Batch") — users revert AI actions, not raw Ctrl+Z steps.
"""

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class IdempotencyRecord(SQLModel, table=True):
    """Maps a client-supplied upload key to the session it created.

    A slow upload can time out client-side even though the server completed it. Without
    this, the automatic retry creates a second orphan session. Kept as its own table so
    `create_all` provisions it on deploy without a schema migration.
    """

    key: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentCommand(SQLModel, table=True):
    """One queued instruction for the local agent, scoped to a session."""

    id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    # Commands applied together (e.g. "Fix all 🟢", or a revert) share a batch_id.
    batch_id: Optional[str] = Field(default=None, index=True)
    kind: str  # apply | highlight | verify | revert
    issue_id: Optional[str] = Field(default=None)
    # Structured, whitelisted op/target descriptor (never a raw Inkscape action string).
    payload_json: str = Field(default="{}")
    status: str = Field(default="pending", index=True)  # pending | done | failed
    # Per-target before-values captured by the agent on apply, for revert/inverse ops.
    before_json: Optional[str] = Field(default=None)
    # Agent's result / error message.
    result_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
