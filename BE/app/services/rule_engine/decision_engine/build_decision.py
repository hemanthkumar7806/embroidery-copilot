"""Build a safe next-action decision from the top cause."""

from __future__ import annotations

from app.services.rule_engine.decision_engine.score_causes import ScoredCause
from app.services.rule_engine.types import Decision


def build_decision(cause: ScoredCause | None) -> Decision:
    if cause is None:
        return Decision(
            main_problem="No file-level issue detected",
            next_action=(
                "Check fabric, stabilizer, thread tension, needle, and machine settings"
            ),
            explanation=(
                "The file structure looks correct, so the issue is likely in the physical setup"
            ),
        )

    if cause.type in ("STATE_DESYNC", "INCONSISTENT_BEHAVIOR", "CORRUPTED_PATH_STATE"):
        return Decision(
            main_problem="Object has inconsistent internal state",
            next_action=(
                "Select the object, run Path > Break Apart, remove extra parts, "
                "then Path > Combine and reapply satin"
            ),
            explanation="Hidden SVG or Ink/Stitch state is causing inconsistent behavior",
        )

    if cause.type == "NARROW_GEOMETRY":
        return Decision(
            main_problem="Geometry is too narrow for stitching",
            next_action="Increase width or switch to running stitch",
            explanation="Very small widths cannot form stable stitches",
        )

    return Decision(
        main_problem=cause.type,
        next_action="Fix the detected issue in the selected object",
        explanation="The file contains a structural issue affecting stitching",
    )
