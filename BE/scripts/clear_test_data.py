#!/usr/bin/env python3
"""Wipe all session/message/analytics data before the beta goes live.

DESTRUCTIVE and irreversible - this deletes every row in the tables below on
whatever DATABASE_URL is configured (local SQLite, or the shared Supabase
Postgres used by both local dev and production). Run once, right before real
users start, to clear out development/test noise.

Usage:
  uv run python scripts/clear_test_data.py           # prompts for confirmation
  uv run python scripts/clear_test_data.py --yes      # skip the prompt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from sqlmodel import Session as DBSession
from sqlmodel import delete

from app.core.config import settings
from app.models.agent import AgentCommand, IdempotencyRecord
from app.models.analytics import (
    AnalyticsEvent,
    AnalyticsMessage,
    AnalyticsSession,
    AnalyticsVisitor,
)
from app.models.session import Message, Session
from app.services.database import database_service

# Children before parents - agentcommand has an FK to session.id, so it must
# be deleted first or Postgres rejects the "session" delete.
TABLES = [
    ("analytics_event", AnalyticsEvent),
    ("analytics_message", AnalyticsMessage),
    ("analytics_session", AnalyticsSession),
    ("analytics_visitor", AnalyticsVisitor),
    ("agentcommand", AgentCommand),
    ("idempotencyrecord", IdempotencyRecord),
    ("message", Message),
    ("session", Session),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    print(f"Target DB: {settings.resolved_database_url}")
    with DBSession(database_service.engine) as db:
        counts = {name: len(db.exec(model.__table__.select()).all()) for name, model in TABLES}

    print("Current row counts:")
    for name, count in counts.items():
        print(f"  {name}: {count}")

    if not any(counts.values()):
        print("Already empty - nothing to do.")
        return

    if not args.yes:
        reply = input("\nDelete ALL rows above? This cannot be undone. Type 'yes' to proceed: ")
        if reply.strip().lower() != "yes":
            print("Aborted.")
            return

    with DBSession(database_service.engine) as db:
        for name, model in TABLES:
            db.exec(delete(model))
        db.commit()

    print("Done - all tables wiped.")


if __name__ == "__main__":
    main()
