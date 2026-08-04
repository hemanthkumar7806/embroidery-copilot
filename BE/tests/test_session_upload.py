"""Tests for uploading SVG into an existing chat session."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import database_service

SQUARE_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkstitch="http://inkstitch.org/namespace"
     width="100mm" height="100mm" viewBox="0 0 100 100">
  <path id="square" d="M 10 10 L 90 10 L 90 90 L 10 90 Z"
        inkstitch:row_spacing_mm="0.4" />
</svg>"""

FIXTURE_SVG = Path(__file__).resolve().parent.parent / "test-fixtures" / "sample.svg"


@pytest.fixture
def client():
    return TestClient(app)


def test_upload_svg_to_chat_session_preserves_history(client: TestClient):
    created = client.post("/api/v1/sessions/chat")
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    chat_before = client.post(
        f"/api/v1/sessions/{session_id}/chat",
        json={"message": "Hello before upload"},
    )
    assert chat_before.status_code == 200

    svg_bytes = FIXTURE_SVG.read_bytes() if FIXTURE_SVG.exists() else SQUARE_SVG
    upload = client.post(
        f"/api/v1/sessions/{session_id}/svg",
        files={"svg_file": ("test.svg", svg_bytes, "image/svg+xml")},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["session_id"] == session_id
    assert "preflight" in body
    # Design sessions have no chat welcome text by design — the report panel is the
    # product. What must be present is the analysis payload.
    assert body["preflight"]["content"] == ""
    assert body["preflight"]["rule_engine"] is not None

    detail = client.get(f"/api/v1/sessions/{session_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["design_report"]["summary"]["element_count"] > 0

    # Prior chat history survives the upload (no welcome message is appended).
    roles = [m["role"] for m in data["chat_history"]]
    assert roles.count("user") >= 1
    assert roles.count("assistant") >= 1

    try:
        database_service.delete_session(session_id)
    except Exception:
        pass
