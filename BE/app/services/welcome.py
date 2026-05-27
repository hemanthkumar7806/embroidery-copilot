"""Deterministic welcome messages after SVG upload (no LLM)."""

from __future__ import annotations

from typing import Any


def _format_stitch_mix(counts: dict[str, int]) -> str:
    if not counts:
        return "no stitch types detected yet"
    parts = [f"{count} {name}" for name, count in sorted(counts.items())]
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def build_welcome_message(report: dict[str, Any], rules: dict[str, Any] | None = None) -> str:
    """Greet the user, summarize the file briefly, and offer a pre-check."""
    summary = report.get("summary") or {}
    doc_name = summary.get("document_name") or "your design"
    element_count = summary.get("element_count", 0)
    stitch_counts = summary.get("stitch_type_counts") or {}
    mix = _format_stitch_mix(stitch_counts)

    lines = [
        f"Hi! I loaded **{doc_name}** — {element_count} embroidery element"
        f"{'s' if element_count != 1 else ''} ({mix}).",
        "",
        "Before I dive in, a couple of quick questions:",
        "- **What are you trying to do?** Run a preflight check, troubleshoot a stitch-out issue, or something else?",
        "- **What fabric and garment is this for?** (e.g. cotton polo, fleece hoodie, cap on twill)",
        "",
        "You can tap a suggestion below, or just type in your own words.",
    ]

    if rules:
        issue_count = len(rules.get("issues") or [])
        gap_count = len(rules.get("context_gaps") or [])
        if issue_count or gap_count:
            lines.append("")
            lines.append(
                f"_I've scanned the file silently ({issue_count} finding"
                f"{'s' if issue_count != 1 else ''} queued). "
                "Say **run preflight check** when you're ready for the full review._"
            )

    return "\n".join(lines)


def build_chat_only_welcome() -> str:
    return (
        "Hi — I'm your Ink/Stitch embroidery assistant.\n\n"
        "Ask me about trims, satins, stabilizer, lettering, or machine setup. "
        "Upload an SVG on the left anytime and I'll ask a few questions before running a pre-check."
    )
