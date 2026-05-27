"""Select the top-scoring cause above the confidence cutoff."""

from __future__ import annotations

from app.services.rule_engine.config import DECISION_CONFIDENCE
from app.services.rule_engine.decision_engine.score_causes import ScoredCause


def select_top_cause(scored: list[ScoredCause]) -> ScoredCause | None:
    if not scored:
        return None
    top = scored[0]
    if top.score < DECISION_CONFIDENCE:
        return None
    return top
