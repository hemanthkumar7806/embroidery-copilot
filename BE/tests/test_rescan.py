"""Tests for the re-scan / Verify loop (step 5)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.api.v1.sessions as sessions_mod
from app.main import app
from app.services.database import database_service


def _fill_svg(row_spacing: str) -> bytes:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:inkstitch="http://inkstitch.org/namespace" '
        'width="100mm" height="100mm" viewBox="0 0 100 100">'
        '<path id="fill1" d="M10,10 L90,10 L90,90 L10,90 Z" style="fill:#cc0000" '
        f'inkstitch:row_spacing_mm="{row_spacing}"/></svg>'
    ).encode()


async def _fake_review(design_report, rules_payload, svg_bytes=None):
    return [
        {
            "id": "ai_thin_0", "category": "ai", "severity": "high", "title": "Thin satin",
            "detail": "d", "suggested_action": "s", "source": "ai", "confidence": 0.9,
            "capability": "guided", "element_ids": [], "focus_bbox": None, "fix": None,
            "sources": [],
        }
    ]


@pytest.fixture
def client():
    return TestClient(app)


def _ids(engine: dict) -> list[str]:
    return [i["id"] for i in engine.get("issues", [])]


def test_rescan_resolves_finding_preserves_fabric_and_ai(client: TestClient, monkeypatch):
    monkeypatch.setattr(sessions_mod, "run_ai_review", _fake_review)

    created = client.post(
        "/api/v1/sessions",
        files={"svg_file": ("dense.svg", _fill_svg("0.25"), "image/svg+xml")},
    )
    assert created.status_code == 200, created.text
    sid = created.json()["session_id"]
    try:
        # Set fabric and add an AI finding.
        client.post(f"/api/v1/sessions/{sid}/context", json={"fabric_type": "fleece"})
        client.post(f"/api/v1/sessions/{sid}/ai-review")

        detail = client.get(f"/api/v1/sessions/{sid}").json()
        cached = detail["design_report"]["cached_rule_engine"]
        assert "row_spacing_too_low" in _ids(cached)  # 0.25 too dense for fleece (0.5-0.6)
        assert any(i["source"] == "ai" for i in cached["issues"])

        # Re-scan with a "fixed" doc: 0.5 spacing (within the fleece band).
        resp = client.post(
            f"/api/v1/sessions/{sid}/rescan",
            files={"svg_file": ("fixed.svg", _fill_svg("0.5"), "image/svg+xml")},
        )
        assert resp.status_code == 200, resp.text
        engine = resp.json()["rule_engine"]

        # The density finding is resolved after the re-scan.
        assert "row_spacing_too_low" not in _ids(engine)
        # Fabric context is preserved.
        assert resp.json()["session_context"]["fabric_type"] == "fleece"
        # Prior AI findings are preserved (not wiped by the rule re-run).
        assert any(i["source"] == "ai" for i in engine["issues"])
    finally:
        try:
            database_service.delete_session(sid)
        except Exception:
            pass
