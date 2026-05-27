"""Validate decision output shape."""

from __future__ import annotations

from app.services.rule_engine.types import Decision


def validate_decision(decision: Decision) -> Decision:
    if not decision.main_problem or not decision.next_action:
        raise ValueError("Invalid decision output")
    if "," in decision.main_problem:
        raise ValueError("Multiple problems detected")
    return decision
