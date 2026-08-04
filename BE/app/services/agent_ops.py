"""Whitelist + sanitization for agent commands, and inverse-op synthesis for revert.

Security posture: the web app and LLM may propose fixes, but only a fixed set of ops
with sanitized operands ever reach the agent — the agent then turns them into Inkscape
action strings. Operands that could break the `action:arg;action:arg` grammar (`;`,
newlines) are rejected here. Attribute names legitimately carry one namespace colon
(e.g. `inkstitch:row_spacing_mm`), so colons are allowed in attribute/id but never in
free values.
"""

from __future__ import annotations

import json
import re
from typing import Any

ALLOWED_KINDS: frozenset[str] = frozenset(
    {"apply", "highlight", "verify", "revert", "rescan"}
)
ALLOWED_OPS: frozenset[str] = frozenset({"set-attribute", "remove-attribute", "simplify"})

# SVG ids / inkstitch attribute names: start with letter/underscore, then word chars,
# and the limited punctuation used by ids and namespaced attributes.
_ID_RE = re.compile(r"^[A-Za-z_][\w:.\-]*$")


class OpValidationError(ValueError):
    """Raised when a command payload is not a safe, whitelisted operation."""


def _check_id(value: Any, what: str) -> None:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise OpValidationError(f"invalid {what}: {value!r}")


def _check_value(value: Any) -> str:
    if not isinstance(value, (str, int, float)):
        raise OpValidationError("value must be a string or number")
    text = str(value)
    if any(ch in text for ch in (";", "\n", "\r")):
        raise OpValidationError("value contains illegal characters (; or newline)")
    return text


def validate_apply_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a 🟢 apply op. Returns the payload unchanged if valid."""
    if not isinstance(payload, dict):
        raise OpValidationError("payload must be an object")
    op = payload.get("op")
    if op not in ALLOWED_OPS:
        raise OpValidationError(f"op not allowed: {op!r}")

    targets = payload.get("target_ids")
    if not isinstance(targets, list) or not targets:
        raise OpValidationError("target_ids is required and must be non-empty")
    for target in targets:
        _check_id(target, "target id")

    if op in ("set-attribute", "remove-attribute"):
        _check_id(payload.get("attribute"), "attribute")
    if op == "set-attribute":
        _check_value(payload.get("value"))
    return payload


def validate_highlight_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OpValidationError("payload must be an object")
    targets = payload.get("target_ids")
    if not isinstance(targets, list) or not targets:
        raise OpValidationError("target_ids is required and must be non-empty")
    for target in targets:
        _check_id(target, "target id")
    return payload


def validate_command(kind: str, payload: dict[str, Any]) -> None:
    """Validate a command by kind; raises OpValidationError on bad input."""
    if kind not in ALLOWED_KINDS:
        raise OpValidationError(f"kind not allowed: {kind!r}")
    if kind == "apply":
        validate_apply_payload(payload)
    elif kind == "highlight":
        validate_highlight_payload(payload)
    # verify / revert reference an issue or batch and carry no direct op to validate.


def inverse_items(batch_commands: list[Any]) -> list[dict[str, Any]]:
    """Synthesize inverse apply-items to revert a batch of applied commands.

    Relies on each applied command's before_json in the generic form
        {target_id: {"attribute": <name>, "old": <value-or-null>}}
    which the agent records at ack time. A null old-value means the attribute did not
    exist before, so the inverse removes it.
    """
    items: list[dict[str, Any]] = []
    for cmd in batch_commands:
        if getattr(cmd, "kind", None) != "apply" or getattr(cmd, "status", None) != "done":
            continue
        before_raw = getattr(cmd, "before_json", None)
        if not before_raw:
            continue
        try:
            before = json.loads(before_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(before, dict):
            continue
        for target_id, info in before.items():
            if not isinstance(info, dict):
                continue
            attribute = info.get("attribute")
            if not attribute:
                continue
            old = info.get("old")
            if old is None:
                inverse = {
                    "op": "remove-attribute",
                    "attribute": attribute,
                    "target_ids": [target_id],
                }
            else:
                inverse = {
                    "op": "set-attribute",
                    "attribute": attribute,
                    "value": str(old),
                    "target_ids": [target_id],
                }
            items.append(
                {"kind": "apply", "issue_id": getattr(cmd, "issue_id", None), "payload": inverse}
            )
    return items
