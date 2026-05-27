"""High-level stitch verdict from rule issues."""

from __future__ import annotations

from app.services.rule_engine.types import EngineDecision, Issue


def get_decision(issues: list[Issue]) -> EngineDecision:
    has_critical = any(issue.severity == "critical" for issue in issues)
    has_high = any(issue.severity == "high" for issue in issues)
    medium_count = sum(1 for issue in issues if issue.severity == "medium")

    if has_critical:
        return EngineDecision(status="FIX_BEFORE_STITCH", reason="Critical issues detected")

    if has_high or medium_count >= 1:
        return EngineDecision(status="CAUTION", reason="Moderate risks detected")

    return EngineDecision(status="SAFE_TO_TEST", reason="No critical issues detected")
