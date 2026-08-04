"""Deterministic welcome messages after SVG upload (no LLM)."""

from __future__ import annotations

from typing import Any


def build_welcome_message(report: dict[str, Any], rules: dict[str, Any] | None = None) -> str:
    """Welcome text for a design session.

    Returns "" by design: the report panel is the product and already states the file,
    the findings and what to do next. A chat greeting would only duplicate it — and an
    empty chat keeps the beta signal honest (people type only if they actually want chat).
    Callers skip storing the message when this is empty.
    """
    return ""


def build_chat_only_welcome() -> str:
    return (
        "Hi — I'm your Ink/Stitch embroidery assistant.\n\n"
        "Ask me about trims, satins, stabilizer, lettering, or machine setup. "
        "Upload an SVG on the left anytime for a full report."
    )
