"""Append-only rule feedback log (JSONL)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

_BE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_FEEDBACK = _BE_ROOT / "data" / "rule_feedback.jsonl"


@dataclass
class FeedbackEntry:
    timestamp: str
    rule_id: str
    design_hash: str
    issue_was_real: bool
    notes: str | None = None


def get_feedback_file_path() -> Path:
    override = os.getenv("RULE_ENGINE_FEEDBACK_PATH")
    return Path(override) if override else _DEFAULT_FEEDBACK


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    return [line for line in raw.split("\n") if line.strip()]


def _parse_jsonl(lines: list[str]) -> list[FeedbackEntry]:
    entries: list[FeedbackEntry] = []
    for line in lines:
        try:
            payload = json.loads(line)
            entries.append(
                FeedbackEntry(
                    timestamp=payload["timestamp"],
                    rule_id=payload["rule_id"],
                    design_hash=payload["design_hash"],
                    issue_was_real=payload["issue_was_real"],
                    notes=payload.get("notes"),
                )
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return entries


def log_feedback(entry: FeedbackEntry) -> None:
    path = get_feedback_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_lines(path)
    existing.append(json.dumps(entry.__dict__, ensure_ascii=False))
    path.write_text("\n".join(existing) + "\n", encoding="utf-8")


def read_all_feedback() -> list[FeedbackEntry]:
    return _parse_jsonl(_read_lines(get_feedback_file_path()))


def get_entry_count(rule_id: str) -> int:
    return sum(1 for entry in read_all_feedback() if entry.rule_id == rule_id)


def get_success_rate(rule_id: str) -> float:
    rows = [entry for entry in read_all_feedback() if entry.rule_id == rule_id]
    if not rows:
        return 1.0
    ok = sum(1 for entry in rows if entry.issue_was_real)
    return ok / len(rows)


def get_rules_with_low_success_rate(threshold: float = 0.4) -> list[str]:
    by_rule: dict[str, list[FeedbackEntry]] = {}
    for entry in read_all_feedback():
        by_rule.setdefault(entry.rule_id, []).append(entry)

    out: list[str] = []
    for rule_id, rows in by_rule.items():
        if len(rows) < 5:
            continue
        ok = sum(1 for entry in rows if entry.issue_was_real)
        if ok / len(rows) < threshold:
            out.append(rule_id)
    return out
