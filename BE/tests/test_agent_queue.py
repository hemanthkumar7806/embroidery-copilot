"""Tests for the agent command queue + AI action history + revert."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import database_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session_id(client: TestClient):
    created = client.post("/api/v1/sessions/chat")
    assert created.status_code == 200
    sid = created.json()["session_id"]
    yield sid
    try:
        database_service.delete_session(sid)
    except Exception:
        pass


def _apply_payload(target: str = "fill1", value: str = "0.4") -> dict:
    return {
        "op": "set-attribute",
        "attribute": "inkstitch:row_spacing_mm",
        "value": value,
        "target_ids": [target],
    }


def test_enqueue_poll_ack_flow(client: TestClient, session_id: str):
    # Enqueue a single apply command.
    resp = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={"kind": "apply", "issue_id": "row_spacing_too_low", "payload": _apply_payload()},
    )
    assert resp.status_code == 200, resp.text
    cmd = resp.json()
    assert cmd["status"] == "pending"
    command_id = cmd["id"]

    # Agent polls and sees it.
    pending = client.get(f"/api/v1/sessions/{session_id}/commands/pending")
    assert pending.status_code == 200
    ids = [c["id"] for c in pending.json()]
    assert command_id in ids

    # Agent acks done with a before-value.
    ack = client.post(
        f"/api/v1/sessions/{session_id}/commands/{command_id}/ack",
        json={
            "status": "done",
            "before": {"fill1": {"attribute": "inkstitch:row_spacing_mm", "old": "0.25"}},
            "result": {"ok": True},
        },
    )
    assert ack.status_code == 200
    assert ack.json()["status"] == "done"

    # No longer pending.
    pending2 = client.get(f"/api/v1/sessions/{session_id}/commands/pending")
    assert command_id not in [c["id"] for c in pending2.json()]


def test_batch_apply_and_revert(client: TestClient, session_id: str):
    # Apply a batch of two fixes.
    resp = client.post(
        f"/api/v1/sessions/{session_id}/commands/batch",
        json={
            "fixes": [
                {"issue_id": "row_spacing_too_low", "payload": _apply_payload("fillA")},
                {"issue_id": "row_spacing_too_low", "payload": _apply_payload("fillB")},
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    cmds = resp.json()
    assert len(cmds) == 2
    batch_id = cmds[0]["batch_id"]
    assert batch_id and all(c["batch_id"] == batch_id for c in cmds)

    # Agent acks both with before-values.
    for c, target in zip(cmds, ("fillA", "fillB")):
        ack = client.post(
            f"/api/v1/sessions/{session_id}/commands/{c['id']}/ack",
            json={
                "status": "done",
                "before": {target: {"attribute": "inkstitch:row_spacing_mm", "old": "0.25"}},
            },
        )
        assert ack.status_code == 200

    # The batch shows up in AI action history and is revertable.
    batches = client.get(f"/api/v1/sessions/{session_id}/batches").json()
    match = [b for b in batches if b["batch_id"] == batch_id]
    assert match and match[0]["revertable"] is True
    assert match[0]["done"] == 2

    # Revert the batch -> two inverse apply commands restoring old values.
    revert = client.post(f"/api/v1/sessions/{session_id}/batches/{batch_id}/revert")
    assert revert.status_code == 200, revert.text
    inv = revert.json()
    assert len(inv) == 2
    assert all(c["payload"]["value"] == "0.25" for c in inv)
    assert all(c["payload"]["op"] == "set-attribute" for c in inv)


def test_rejects_unsafe_payload(client: TestClient, session_id: str):
    # Value containing an action separator must be rejected.
    bad = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={
            "kind": "apply",
            "payload": {
                "op": "set-attribute",
                "attribute": "inkstitch:row_spacing_mm",
                "value": "0.4;delete-selection",
                "target_ids": ["fill1"],
            },
        },
    )
    assert bad.status_code == 400

    # Unknown op rejected.
    bad_op = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={"kind": "apply", "payload": {"op": "eval", "target_ids": ["x"]}},
    )
    assert bad_op.status_code == 400

    # Unknown kind rejected.
    bad_kind = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={"kind": "danger", "payload": {}},
    )
    assert bad_kind.status_code == 400
