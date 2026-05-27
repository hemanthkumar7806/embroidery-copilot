"""Thresholds and constants for the rule engine."""

from __future__ import annotations

DECISION_CONFIDENCE = 0.8
DECISION_MEDIUM_CONFIDENCE = 0.6

STRETCHY_FABRICS: tuple[str, ...] = (
    "jersey",
    "knit",
    "stretch",
    "lycra",
    "spandex",
    "fleece",
    "hoodie",
    "polo",
    "pique",
    "sherpa",
    "terry",
    "sweatshirt",
)

ROW_SPACING_TOO_HIGH_MM = 0.7
SATIN_MIN_STITCH_LENGTH_MM = 0.4
RUNNING_MIN_STITCH_LENGTH_MM = 1.5
SATIN_MIN_WIDTH_MM = 1.5
CRITICAL_MIN_WIDTH_MM = 1.0
PULL_COMP_STRETCHY_MIN_MM = 0.15
EXTREME_EXPAND_MM = 4.0

MACHINE_FORMATS: tuple[str, ...] = ("dst", "pes", "jef", "vp3", "exp", "hus")

UNDERLAY_PARAM_KEYS: tuple[str, ...] = (
    "fill_underlay",
    "contour_underlay",
    "zigzag_underlay",
    "center_walk_underlay",
    "edge_walk_underlay",
    "satin_underlay",
)

FILL_MIN_WIDTH_MM = 2.0

CONTEXT_GAP_RULE_IDS: frozenset[str] = frozenset(
    {
        "missing_metadata",
        "fabric_instability_risk",
        "fabric_type_unknown",
        "trim_behavior_risk",
        "export_param_mismatch_risk",
        "hoop_size_not_set",
        "insufficient_data_risk",
    }
)

SYMPTOM_FREEZE_IDS: frozenset[str] = frozenset(
    {"save_or_simulator_freeze", "export_failure"}
)
SYMPTOM_PUCKER_IDS: frozenset[str] = frozenset({"puckering_distortion"})
SYMPTOM_BREAK_IDS: frozenset[str] = frozenset({"thread_break"})

FREEZE_BOOST_RULES: frozenset[str] = frozenset(
    {
        "simulation_freeze_risk",
        "high_node_count",
        "excessive_fragmentation",
        "over_detailed_path",
        "high_complexity_design",
    }
)
PUCKER_BOOST_RULES: frozenset[str] = frozenset(
    {
        "extreme_density",
        "pull_compensation_missing",
        "stretchy_fabric_no_underlay",
        "row_spacing_too_low",
    }
)
BREAK_BOOST_RULES: frozenset[str] = frozenset(
    {"row_spacing_too_low", "stitch_length_too_short"}
)

SYMPTOM_CONFIDENCE_BOOST = 0.12
