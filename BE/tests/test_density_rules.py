"""Tests for fabric-aware density detection (step 3)."""

from __future__ import annotations

from app.services.rule_engine.runner import _resolve_issue_severity, get_rule_by_id
from app.services.rule_engine.types import DesignReport


def _report(row_spacing: float, fabric: str | None = None) -> DesignReport:
    return DesignReport(
        parameters={"row_spacing_mm": row_spacing},
        physical={"fabric_type": fabric} if fabric else {},
    )


LOW = get_rule_by_id("row_spacing_too_low")
HIGH = get_rule_by_id("row_spacing_too_high")


def test_too_low_is_fabric_aware():
    # 0.45 is fine on cotton (band 0.4-0.5) but too dense on fleece (band 0.5-0.6).
    assert LOW.check(_report(0.45, "cotton")) is False
    assert LOW.check(_report(0.45, "fleece")) is True
    # 0.35 is fine on denim (0.3-0.45) but too dense on fleece.
    assert LOW.check(_report(0.35, "denim")) is False
    assert LOW.check(_report(0.35, "fleece")) is True


def test_too_high_is_fabric_aware():
    # 0.55 shows gaps on cotton (max 0.5) but is fine on fleece (max 0.6).
    assert HIGH.check(_report(0.55, "cotton")) is True
    assert HIGH.check(_report(0.55, "fleece")) is False
    assert HIGH.check(_report(0.65, "fleece")) is True


def test_unknown_fabric_matches_old_thresholds():
    # DEFAULT band 0.35-0.7 == the previous universal literals.
    assert LOW.check(_report(0.30)) is True
    assert LOW.check(_report(0.45)) is False
    assert HIGH.check(_report(0.75)) is True
    assert HIGH.check(_report(0.6)) is False


def test_hard_floor_is_critical_on_any_fabric():
    # Below the universal 0.25mm floor -> critical, regardless of fabric band.
    assert _resolve_issue_severity(LOW, _report(0.2, "cotton")) == "critical"
    assert _resolve_issue_severity(LOW, _report(0.2, None)) == "critical"
    # Above the floor -> the rule's base severity.
    assert _resolve_issue_severity(LOW, _report(0.35, "fleece")) == "high"


def test_detail_names_fabric_and_band():
    detail = LOW.detail(_report(0.45, "fleece"))
    assert "fleece" in detail
    assert "0.5" in detail and "0.6" in detail
