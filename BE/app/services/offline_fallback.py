"""Offline fallback responses when no LLM API key is configured."""

from __future__ import annotations

from typing import Any


def _summary_line(design_report: dict[str, Any]) -> str:
    summary = design_report.get("summary") or {}
    counts = summary.get("stitch_type_counts") or {}
    return (
        f"{summary.get('element_count', 0)} stitchable elements; "
        f"stitch mix {counts}; hidden layers {summary.get('hidden_layer_count', 0)}"
    )


def build_offline_preflight(design_report: dict[str, Any]) -> str:
    summary = design_report.get("summary") or {}
    counts = summary.get("stitch_type_counts") or {}
    hidden = summary.get("hidden_layer_count", 0)

    return f"""### What's actually wrong
- Design may have **satin vs fill mismatch** if small satins or tight columns are present ({counts.get('satin', 0)} satin, {counts.get('fill', 0)} fill, {counts.get('stroke', 0)} stroke/run).
- **Hidden layers / duplicate objects** can still stitch ({hidden} hidden layer(s) flagged in the SVG scan).
- **Spacing vs trims** may bite if lettering or run paths are tight and `trim_after` is enabled on adjacent objects.

### What your tools found
{_summary_line(design_report)}
Open paths: {summary.get('open_path_count', 0)}; closed paths: {summary.get('closed_path_count', 0)}.
Complexity hint: {summary.get('estimated_complexity_hint', 'n/a')}.

### What to do RIGHT NOW
1. **Digitizing:** unlock layers, delete duplicates, confirm each shape uses the right stitch type (satin only where columns are wide enough).
2. **Machine:** run a short trim test on scrap — confirm trims fire and jump stitches are acceptable.
3. **Fabric/stabilizer:** match stabilizer weight to fabric (cutaway for knits/polo, appropriate density for the stitch mix).
4. Re-export PES and compare preview vs machine on one color first.

### Why it happened
Ink/Stitch params and layer visibility often override what you see on screen; tight spacing and wrong stitch type show up as bird-nesting, gaps, or missing trims on the machine.

**Do this first:**
1. Show all layers and stitch a visibility check swatch.
2. Verify satin width vs column settings.
3. Test trims on scrap before full run.
4. Confirm stabilizer matches fabric.
"""


def build_offline_chat_reply(design_report: dict[str, Any], user_message: str) -> str:
    return (
        f"Offline beta mode (no LLM key configured). Based on the uploaded file: {_summary_line(design_report)}. "
        f"You asked: \"{user_message}\". "
        "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in `.env` for full AI answers."
    )
