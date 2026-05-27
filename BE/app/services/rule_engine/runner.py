"""Rule engine runner — evaluates all rules and builds structured output."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.services.rule_engine.config import (
    BREAK_BOOST_RULES,
    CONTEXT_GAP_RULE_IDS,
    CRITICAL_MIN_WIDTH_MM,
    FREEZE_BOOST_RULES,
    PUCKER_BOOST_RULES,
    SATIN_MIN_WIDTH_MM,
    SYMPTOM_BREAK_IDS,
    SYMPTOM_CONFIDENCE_BOOST,
    SYMPTOM_FREEZE_IDS,
    SYMPTOM_PUCKER_IDS,
)
from app.services.rule_engine.decision import get_decision
from app.services.rule_engine.decision_engine.build_decision import build_decision
from app.services.rule_engine.decision_engine.classifier import classify_failure
from app.services.rule_engine.decision_engine.mismatch import detect_mismatch
from app.services.rule_engine.decision_engine.normalize_design_report import (
    normalize_design_report_for_decision,
)
from app.services.rule_engine.decision_engine.score_causes import ScoredCause, score_causes
from app.services.rule_engine.decision_engine.select_top import select_top_cause
from app.services.rule_engine.decision_engine.state_risk import detect_state_risk
from app.services.rule_engine.decision_engine.validate_decision import validate_decision
from app.services.rule_engine.feedback import get_entry_count, get_success_rate
from app.services.rule_engine.gap_tracker import analyze_gaps
from app.services.rule_engine.rules.export_ import export_rules
from app.services.rule_engine.rules.geometry import geometry_rules
from app.services.rule_engine.rules.parameters import parameter_rules
from app.services.rule_engine.rules.performance import performance_rules
from app.services.rule_engine.rules.physical import physical_rules
from app.services.rule_engine.rules.routing import routing_rules
from app.services.rule_engine.rules.structure import structure_rules
from app.services.rule_engine.rules.system import system_rules
from app.services.rule_engine.types import (
    Category,
    ConfidenceTier,
    DesignReport,
    DryRunEvaluation,
    Issue,
    Rule,
    RuleEngineOptions,
    RuleEngineResult,
    Severity,
)

ALL_RULES: list[Rule] = [
    *geometry_rules,
    *parameter_rules,
    *structure_rules,
    *routing_rules,
    *export_rules,
    *physical_rules,
    *performance_rules,
    *system_rules,
]

SEVERITY_ORDER: dict[Severity, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def _to_confidence_tier(value: float) -> ConfidenceTier:
    if value >= 0.98:
        return "certain"
    if value >= 0.8:
        return "high"
    if value >= 0.5:
        return "medium"
    return "low"


def _to_root_cause(cause: ScoredCause | None):
    from app.services.rule_engine.types import RootCause

    if cause is None:
        return None

    if cause.type == "STATE_DESYNC":
        return RootCause(
            id=cause.type,
            cause="Object has inconsistent internal state",
            action=(
                "Select the object, run Path > Break Apart, remove extra parts, "
                "then Path > Combine and reapply satin"
            ),
            confidence="high",
        )

    if cause.type in ("INCONSISTENT_BEHAVIOR", "CORRUPTED_PATH_STATE"):
        return RootCause(
            id=cause.type,
            cause="Hidden SVG or Ink/Stitch state is causing inconsistent behavior",
            action=(
                "Select the object, run Path > Break Apart, remove extra parts, "
                "then Path > Combine and reapply satin"
            ),
            confidence="high",
        )

    if cause.type == "NARROW_GEOMETRY":
        return RootCause(
            id=cause.type,
            cause="Geometry is too narrow for stitching",
            action="Increase width or switch to running stitch",
            confidence="medium",
        )

    if cause.rule_issue is not None:
        issue = cause.rule_issue
        return RootCause(
            id=issue.id,
            cause=issue.title,
            action=issue.suggested_action,
            confidence=_to_confidence_tier(cause.confidence),
        )

    return RootCause(
        id=cause.type,
        cause=cause.type,
        action="Fix the detected issue in the selected object",
        confidence=_to_confidence_tier(cause.confidence),
    )


def _empty_by_severity() -> dict[Severity, int]:
    return {"critical": 0, "high": 0, "medium": 0, "low": 0}


def _empty_by_category() -> dict[Category, int]:
    return {
        "geometry": 0,
        "parameters": 0,
        "structure": 0,
        "routing": 0,
        "export": 0,
        "physical": 0,
        "performance": 0,
    }


def _downgrade_severity(severity: Severity) -> Severity:
    mapping: dict[Severity, Severity] = {
        "critical": "high",
        "high": "medium",
        "medium": "low",
        "low": "low",
    }
    return mapping[severity]


def _apply_feedback_adjustments(issues: list[Issue]) -> None:
    for issue in issues:
        count = get_entry_count(issue.id)
        rate = get_success_rate(issue.id)
        if count >= 5 and rate < 0.4:
            issue.severity = _downgrade_severity(issue.severity)
            issue.adjustment_note = (
                f"Severity reduced: success rate {rate * 100:.0f}% across {count} feedback samples"
            )


def _build_summary(issues: list[Issue]) -> dict[str, Any]:
    by_severity = _empty_by_severity()
    by_category = _empty_by_category()
    for issue in issues:
        by_severity[issue.severity] += 1
        by_category[issue.category] += 1

    highest_risk_category: Category | None = None
    best_count = 0
    for category, count in by_category.items():
        if count > best_count:
            best_count = count
            highest_risk_category = category
    if not issues:
        highest_risk_category = None

    return {
        "total": len(issues),
        "by_severity": by_severity,
        "by_category": by_category,
        "highest_risk_category": highest_risk_category,
    }


def _split_issues(issues: list[Issue]) -> tuple[list[Issue], list[Issue]]:
    real = [issue for issue in issues if issue.id not in CONTEXT_GAP_RULE_IDS]
    gaps = [issue for issue in issues if issue.id in CONTEXT_GAP_RULE_IDS]
    return real, gaps


def _symptom_confidence_boost(rule_id: str, report: DesignReport) -> float:
    symptom = str((report.meta or {}).get("symptom") or "")
    if symptom in SYMPTOM_FREEZE_IDS and rule_id in FREEZE_BOOST_RULES:
        return SYMPTOM_CONFIDENCE_BOOST
    if symptom in SYMPTOM_PUCKER_IDS and rule_id in PUCKER_BOOST_RULES:
        return SYMPTOM_CONFIDENCE_BOOST
    if symptom in SYMPTOM_BREAK_IDS and rule_id in BREAK_BOOST_RULES:
        return SYMPTOM_CONFIDENCE_BOOST
    return 0.0


def _resolve_issue_severity(rule: Rule, report: DesignReport) -> Severity:
    if rule.id == "over_detailed_path":
        avg = report.geometry.get("avg_segment_length_mm")
        if avg is not None and avg < 0.3:
            return "high"

    if rule.id == "narrow_geometry_stitch_mismatch":
        min_dim = report.geometry.get("min_dimension_mm")
        if min_dim is not None and min_dim < CRITICAL_MIN_WIDTH_MM:
            return "critical"
        if min_dim is not None and min_dim < SATIN_MIN_WIDTH_MM:
            return "high"

    return rule.severity


def get_rule_by_id(rule_id: str) -> Rule | None:
    return next((rule for rule in ALL_RULES if rule.id == rule_id), None)


def get_all_rules() -> list[Rule]:
    return ALL_RULES


def run_rule_engine(
    report: DesignReport,
    options: RuleEngineOptions | None = None,
) -> RuleEngineResult:
    opts = options or RuleEngineOptions()
    evaluations: list[DryRunEvaluation] = []
    issues: list[Issue] = []

    for rule in ALL_RULES:
        skipped = rule.skip_when(report) if rule.skip_when else False
        effective_confidence = min(1.0, rule.confidence + _symptom_confidence_boost(rule.id, report))
        meets_confidence_threshold = effective_confidence >= opts.min_confidence
        check_result = False if skipped else rule.check(report)
        fired = not skipped and meets_confidence_threshold and check_result

        evaluations.append(
            DryRunEvaluation(
                rule_id=rule.id,
                fired=fired,
                skipped=skipped,
                meets_confidence_threshold=meets_confidence_threshold,
                confidence=effective_confidence,
            )
        )

        if fired:
            issue = Issue(
                id=rule.id,
                category=rule.category,
                severity=_resolve_issue_severity(rule, report),
                confidence=effective_confidence,
                title=rule.title,
                detail=rule.detail(report),
                source=rule.source,
                suggested_action=rule.suggested_action,
                group=rule.group,
                evidence=rule.evidence(report) if rule.evidence else None,
            )
            issues.append(issue)

    issues.sort(key=lambda issue: SEVERITY_ORDER[issue.severity])

    _apply_feedback_adjustments(issues)

    real_issues, context_gap_issues = _split_issues(issues)

    summary = _build_summary(real_issues)
    classification = classify_failure(report, real_issues)
    normalized = normalize_design_report_for_decision(report)
    state_risks = detect_state_risk(normalized)
    mismatch_issues = detect_mismatch(normalized)
    scored_causes = score_causes(
        rule_issues=real_issues,
        state_risks=state_risks,
        mismatch_issues=mismatch_issues,
    )
    scored_root_cause = select_top_cause(scored_causes)
    root_cause = _to_root_cause(scored_root_cause)
    strict_decision = build_decision(scored_root_cause)
    detailed_decision = validate_decision(strict_decision)
    gaps = analyze_gaps(
        report,
        {"issues": real_issues, "dry_run_evaluations": evaluations},
        ALL_RULES,
    )
    decision = get_decision(real_issues)

    return RuleEngineResult(
        issues=real_issues,
        context_gap_issues=context_gap_issues,
        classification=classification,
        root_cause=root_cause,
        detailed_decision=detailed_decision,
        summary=summary,
        gaps=gaps,
        dry_run_evaluations=evaluations if opts.dry_run else None,
        decision=decision,
    )


def result_to_dict(result: RuleEngineResult) -> dict[str, Any]:
    """Serialize engine output for API / LLM prompts."""

    def _issue(issue: Issue) -> dict[str, Any]:
        payload = asdict(issue)
        return payload

    return {
        "issues": [_issue(issue) for issue in result.issues],
        "context_gaps": [_issue(issue) for issue in result.context_gap_issues],
        "classification": asdict(result.classification),
        "root_cause": asdict(result.root_cause) if result.root_cause else None,
        "detailed_decision": asdict(result.detailed_decision),
        "summary": result.summary,
        "gaps": asdict(result.gaps),
        "decision": asdict(result.decision),
    }


def run(report: DesignReport | dict[str, Any]) -> dict[str, Any]:
    """Public entrypoint: accept DesignReport or raw svg_parser dict."""
    if isinstance(report, dict):
        from app.services.rule_engine.normalizer import normalize_design_report

        normalized = normalize_design_report(report)
    else:
        normalized = report
    return result_to_dict(run_rule_engine(normalized))
