"""Gap analysis for uncovered report fields and low-confidence rules."""

from __future__ import annotations

from typing import Any

from app.services.rule_engine.types import DesignReport, DryRunEvaluation, GapReport, Issue, Rule

CANONICAL_LEAF_PATHS: list[str] = [
    "geometry.node_count",
    "geometry.path_count",
    "geometry.bounding_box",
    "geometry.has_open_paths",
    "geometry.open_path_count",
    "geometry.overlap_ratio",
    "geometry.path_length_mm",
    "geometry.avg_segment_length_mm",
    "geometry.min_dimension_mm",
    "summary.total_path_length_mm",
    "summary.avg_segment_length_global",
    "parameters.row_spacing_mm",
    "parameters.stitch_length_mm",
    "parameters.pull_compensation_mm",
    "parameters.density_value",
    "structure.layer_count",
    "structure.has_hidden_layers",
    "structure.has_underlay",
    "structure.stitch_types",
    "structure.element_count",
    "routing.jump_stitch_count",
    "routing.trim_count",
    "routing.color_change_count",
    "routing.estimated_stitch_count",
    "routing.has_short_runs",
    "export.format",
    "export.software_version",
    "export.has_metadata",
    "physical.fabric_type",
    "physical.hoop_size_mm",
    "physical.machine_type",
]


def analyze_gaps(
    report: DesignReport,
    result: dict[str, Any],
    all_rules: list[Rule],
) -> GapReport:
    issues: list[Issue] = result["issues"]
    dry_run_evaluations: list[DryRunEvaluation] | None = result.get("dry_run_evaluations")

    all_read_fields = {field for rule in all_rules for field in rule.fields}
    unchecked_fields = [path for path in CANONICAL_LEAF_PATHS if path not in all_read_fields]

    low_confidence_rules = [rule.id for rule in all_rules if rule.confidence < 0.6]

    physical_null_fields: list[str] = []
    if report.physical.get("fabric_type") is None:
        physical_null_fields.append("fabric_type")
    if report.physical.get("hoop_size_mm") is None:
        physical_null_fields.append("hoop_size_mm")
    if report.physical.get("machine_type") is None:
        physical_null_fields.append("machine_type")

    skipped_rules = [
        evaluation.rule_id
        for evaluation in (dry_run_evaluations or [])
        if evaluation.skipped
    ]

    soft_rules = [issue.id for issue in issues if issue.confidence < 0.7]

    return GapReport(
        unchecked_fields=unchecked_fields,
        low_confidence_rules=low_confidence_rules,
        missing_physical_data=physical_null_fields,
        soft_rules=soft_rules,
        skipped_rules=skipped_rules,
    )


def flatten_report_paths(obj: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if obj is None or not isinstance(obj, (dict, list)):
        if prefix:
            keys.add(prefix)
        return keys
    if isinstance(obj, list):
        if prefix:
            keys.add(prefix)
        return keys
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(flatten_report_paths(value, path))
        else:
            keys.add(path)
    return keys
