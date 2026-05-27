"""Embroidery rule engine — structured findings for preflight and chat."""

from app.services.rule_engine.normalizer import normalize_design_report, resolve_stitch_type
from app.services.rule_engine.runner import (
    ALL_RULES,
    SEVERITY_ORDER,
    get_all_rules,
    get_rule_by_id,
    result_to_dict,
    run,
    run_rule_engine,
)

__all__ = [
    "ALL_RULES",
    "SEVERITY_ORDER",
    "get_all_rules",
    "get_rule_by_id",
    "normalize_design_report",
    "resolve_stitch_type",
    "result_to_dict",
    "run",
    "run_rule_engine",
]
