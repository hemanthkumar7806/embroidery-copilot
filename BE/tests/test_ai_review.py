"""Tests for the LLM review pass (step 2)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.api.v1.sessions as sessions_mod
from app.main import app
from app.services.ai_review import (
    _clip_text,
    _compact_elements,
    build_review_messages,
    parse_findings,
    AIReviewInputs,
)
from app.services.database import database_service

FILL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'xmlns:inkstitch="http://inkstitch.org/namespace" '
    'width="100mm" height="100mm" viewBox="0 0 100 100">'
    '<path id="fill1" d="M10,10 L90,10 L90,90 L10,90 Z" style="fill:#cc0000" '
    'inkstitch:row_spacing_mm="0.25"/></svg>'
).encode()


def _report() -> dict:
    return {
        "elements": [
            {"id": "a", "stitch_type": "satin", "min_dimension_mm": 0.8,
             "bounding_box": {"x": 0, "y": 0, "w": 1, "h": 30}},
            {"id": "b", "stitch_type": "fill", "min_dimension_mm": 20,
             "bounding_box": {"x": 5, "y": 5, "w": 40, "h": 40}},
        ],
        "summary": {"element_count": 2},
        "structure": {"stitch_types": ["satin", "fill"]},
        "physical": {"fabric_type": "fleece"},
    }


# ------------------------------- unit ------------------------------- #


def test_parse_findings_validates_and_filters():
    text = """```json
    [
      {"title": "Thin satin", "detail": "too narrow", "suggested_action": "widen",
       "capability": "guided", "severity": "high", "confidence": 0.9,
       "element_ids": ["a", "ghost"]},
      {"title": "Should be dropped", "capability": "auto_fix", "element_ids": []},
      {"title": "", "capability": "recommendation"},
      {"title": "Busy layout", "detail": "d", "suggested_action": "s",
       "capability": "recommendation", "severity": "nonsense", "confidence": 2.0,
       "element_ids": []}
    ]
    ```"""
    findings = parse_findings(text, _report())
    assert len(findings) == 2  # auto_fix + empty-title dropped

    thin = findings[0]
    assert thin["capability"] == "guided"
    assert thin["source"] == "ai"
    assert thin["element_ids"] == ["a"]  # "ghost" filtered out
    assert thin["focus_bbox"] is not None
    assert thin["fix"] is None

    layout = findings[1]
    assert layout["capability"] == "recommendation"
    assert layout["severity"] == "medium"  # "nonsense" normalized
    assert layout["confidence"] == 1.0  # clamped
    assert layout["element_ids"] == []


def test_clip_text_breaks_on_word_boundary_under_limit():
    short = "Row spacing is too low for cotton."
    assert _clip_text(short) == short  # untouched, well under the cap


def test_clip_text_truncates_long_text_at_a_word_boundary():
    long_text = (
        "The fabric type is currently unknown. Optimal stitch density, underlay type, "
        "and pull compensation are highly dependent on the fabric (e.g., cotton, "
        "fleece, denim, stretchy knits). Without this information, precise "
        "recommendations for the fill elements cannot be made."
    )
    clipped = _clip_text(long_text, limit=100)
    assert len(clipped) <= 101  # 100 + the ellipsis char
    assert clipped.endswith("…")
    assert not clipped[:-1].endswith(" ")  # no trailing space before the ellipsis
    # Never cut a word in half — the text up to the ellipsis is a prefix made of
    # whole words from the original.
    assert long_text.startswith(clipped[:-1].rstrip(".,;:"))


def test_parse_findings_clips_overlong_ai_detail():
    long_detail = (
        "The fabric type is currently unknown. Optimal stitch density, underlay type, "
        "and pull compensation are highly dependent on the fabric such as cotton, "
        "fleece, denim, or stretchy knits, and without this information precise "
        "recommendations for these fill elements genuinely cannot be made at all."
    )
    assert len(long_detail) > 220
    text = json.dumps([
        {"title": "Missing Fabric Information", "detail": long_detail,
         "suggested_action": "set the fabric", "capability": "recommendation",
         "severity": "critical", "confidence": 0.9, "element_ids": []}
    ])
    findings = parse_findings(text, _report())
    assert len(findings) == 1
    assert len(findings[0]["detail"]) <= 221  # MAX_DETAIL_CHARS + ellipsis
    assert findings[0]["detail"].endswith("…")


def test_parse_findings_handles_garbage():
    assert parse_findings("not json at all", _report()) == []
    assert parse_findings("", _report()) == []


def test_parse_findings_maps_source_refs_to_citations():
    chunks = [
        {"metadata": {"source_file": "sources-inkstitch.md", "section_title": "fill",
                      "source_url": "u1"}},
        {"metadata": {"source_file": "sources-wilcom.md", "section_title": "underlay",
                      "source_url": "u2"}},
    ]
    text = (
        '[{"title": "Underlay", "detail": "d", "suggested_action": "s", '
        '"capability": "guided", "severity": "high", "confidence": 0.9, '
        '"element_ids": [], "source_refs": [2, 99]}]'
    )
    findings = parse_findings(text, _report(), chunks)
    assert len(findings) == 1
    sources = findings[0]["sources"]
    assert len(sources) == 1  # ref 2 valid; 99 out-of-range dropped
    assert sources[0]["source_file"] == "sources-wilcom.md"


def test_parse_findings_without_chunks_has_no_sources():
    text = (
        '[{"title": "X", "detail": "d", "suggested_action": "s", "capability": '
        '"recommendation", "severity": "low", "confidence": 0.5, "element_ids": [], '
        '"source_refs": [1]}]'
    )
    findings = parse_findings(text, _report())  # no chunks -> graceful
    assert findings[0]["sources"] == []


def _report_with_params() -> dict:
    """Two cotton fills: one below the density floor, one squarely in-band."""
    return {
        "elements": [
            {"id": "bad", "stitch_type": "fill", "min_dimension_mm": 20,
             "bounding_box": {"x": 0, "y": 0, "w": 20, "h": 20},
             "params": {"row_spacing_mm": "0.1"}},
            {"id": "good", "stitch_type": "fill", "min_dimension_mm": 20,
             "bounding_box": {"x": 50, "y": 0, "w": 20, "h": 20},
             "params": {"row_spacing_mm": "0.45"}},
        ],
        "summary": {"element_count": 2},
        "structure": {"stitch_types": ["fill"]},
        "physical": {"fabric_type": "cotton"},
    }


def _report_two_separate_rects() -> dict:
    """Two fills nowhere near each other — not stacked by any definition."""
    return {
        "elements": [
            {"id": "r1", "stitch_type": "fill", "min_dimension_mm": 20,
             "bounding_box": {"x": 0, "y": 0, "w": 20, "h": 20}},
            {"id": "r2", "stitch_type": "fill", "min_dimension_mm": 20,
             "bounding_box": {"x": 100, "y": 100, "w": 20, "h": 20}},
        ],
        "summary": {"element_count": 2},
        "structure": {"stitch_types": ["fill"]},
        "physical": {},
    }


def test_compact_elements_includes_bbox_and_params():
    compact = _compact_elements(_report_with_params())
    bad = next(e for e in compact if e["id"] == "bad")
    assert bad["bbox_mm"] == {"x": 0, "y": 0, "w": 20, "h": 20}
    assert bad["params"]["row_spacing_mm"] == 0.1


def test_parse_findings_drops_duplicate_of_existing_rule():
    """The model repeated a finding it was told about — code drops it even though the
    prompt already says not to, since the prompt alone didn't hold in practice."""
    text = (
        '[{"title": "Missing Underlay", "detail": "underlay is missing on these fills", '
        '"suggested_action": "add underlay", "capability": "recommendation", '
        '"severity": "critical", "confidence": 0.9, "element_ids": []}]'
    )
    existing = [{"id": "missing_underlay", "title": "Fill without underlay"}]
    assert parse_findings(text, _report(), existing_issues=existing) == []


def test_parse_findings_keeps_unrelated_finding_despite_existing_issues():
    text = (
        '[{"title": "Small text", "detail": "the lettering looks too small to stitch '
        'legibly", "suggested_action": "enlarge text", "capability": "recommendation", '
        '"severity": "medium", "confidence": 0.8, "element_ids": []}]'
    )
    existing = [{"id": "missing_underlay", "title": "Fill without underlay"}]
    findings = parse_findings(text, _report(), existing_issues=existing)
    assert len(findings) == 1


def test_parse_findings_strips_element_ids_the_data_disagrees_with():
    """AI names a good element alongside a bad one for a checkable claim — only the
    element whose real value actually violates the threshold survives."""
    text = (
        '[{"title": "Row spacing concern", "detail": "the row spacing is too low here", '
        '"suggested_action": "increase it", "capability": "recommendation", '
        '"severity": "high", "confidence": 0.8, "element_ids": ["bad", "good"]}]'
    )
    findings = parse_findings(text, _report_with_params())
    assert len(findings) == 1
    assert findings[0]["element_ids"] == ["bad"]


def test_parse_findings_drops_density_claim_when_nothing_verifies():
    text = (
        '[{"title": "Row spacing concern", "detail": "the row spacing is too low here", '
        '"suggested_action": "increase it", "capability": "recommendation", '
        '"severity": "high", "confidence": 0.8, "element_ids": ["good"]}]'
    )
    assert parse_findings(text, _report_with_params()) == []


def test_parse_findings_drops_false_stacking_claim():
    text = (
        '[{"title": "Optimize stacked fills", "detail": "these shapes are stacked and '
        'overlapping", "suggested_action": "digitize center-out", '
        '"capability": "recommendation", "severity": "low", "confidence": 0.7, '
        '"element_ids": ["r1", "r2"]}]'
    )
    assert parse_findings(text, _report_two_separate_rects()) == []


def test_build_review_messages_is_structured_without_image():
    msgs = build_review_messages(
        AIReviewInputs(design_report=_report(), fabric="fleece", rules_payload={"issues": []},
                       rag_context="docs")
    )
    assert len(msgs) == 2
    assert isinstance(msgs[1].content, str)  # no image -> plain text
    assert "fleece" in msgs[1].content


def test_build_review_messages_flags_truncation(monkeypatch):
    import app.services.ai_review as ai_review_mod

    monkeypatch.setattr(ai_review_mod, "MAX_ELEMENTS_FOR_REVIEW", 1)
    msgs = build_review_messages(
        AIReviewInputs(design_report=_report(), fabric="fleece", rules_payload={"issues": []},
                       rag_context="docs")
    )
    assert '"elements_truncated": true' in msgs[1].content


# --------------------------- integration ---------------------------- #


@pytest.fixture
def client():
    return TestClient(app)


async def _fake_review(design_report, rules_payload, svg_bytes=None):
    return [
        {
            "id": "ai_thin_satin_0", "category": "ai", "severity": "high",
            "title": "Thin satin", "detail": "too narrow for satin on fleece",
            "suggested_action": "Widen or convert to running stitch", "source": "ai",
            "confidence": 0.9, "capability": "guided", "element_ids": [], "focus_bbox": None,
            "fix": None,
        }
    ]


def test_ai_review_endpoint_merges_and_is_idempotent(client: TestClient, monkeypatch):
    monkeypatch.setattr(sessions_mod, "run_ai_review", _fake_review)
    created = client.post(
        "/api/v1/sessions", files={"svg_file": ("fill.svg", FILL_SVG, "image/svg+xml")}
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]
    try:
        resp = client.post(f"/api/v1/sessions/{session_id}/ai-review")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ai_reviewed"] is True
        ai = [i for i in body["rule_engine"]["issues"] if i["source"] == "ai"]
        assert len(ai) == 1
        assert ai[0]["capability"] == "guided"

        # Deterministic 🟢 issue from the rules is still present alongside the AI finding.
        assert any(i["id"] == "row_spacing_too_low" for i in body["rule_engine"]["issues"])

        # Idempotent: a second run does not stack duplicate AI findings.
        resp2 = client.post(f"/api/v1/sessions/{session_id}/ai-review")
        ai2 = [i for i in resp2.json()["rule_engine"]["issues"] if i["source"] == "ai"]
        assert len(ai2) == 1
    finally:
        try:
            database_service.delete_session(session_id)
        except Exception:
            pass
