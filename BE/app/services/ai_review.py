"""LLM 'senior digitizer' review pass — adds 🟡/🔵 judgment findings the rules miss.

Structured-first, vision-ready: `AIReviewInputs` carries an optional image so a rendered
PNG can be added later without changing the message assembly. LLM findings are always
guided/recommendation (never auto_fix) — the user stays in control.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.core.logging import logger
from app.core.prompts import load_ai_review_prompt
from app.services.issue_element_mapper import (
    _element_bbox,
    _union_bbox,
    _valid_elements,
    build_instances,
    resolve_issue_targets,
)
from app.services.llm import llm_service
from app.services.rag import rag_service
from app.services.rule_engine.normalizer import _collect_stitch_length_mm
from app.services.rule_engine.normalizer import _num as _parse_num
from app.services.svg_render import render_svg_to_png

_ALLOWED_CAPS = {"guided", "recommendation"}
_ALLOWED_SEV = {"critical", "high", "medium", "low"}
MAX_FINDINGS = 8
# Keeps the prompt bounded on very large designs — the model still gets accurate
# per-element data, just not for every single shape past this count.
MAX_ELEMENTS_FOR_REVIEW = 60


@dataclass
class AIReviewInputs:
    design_report: dict[str, Any]
    fabric: str | None
    rules_payload: dict[str, Any]
    rag_context: str
    image: bytes | None = None  # vision-ready seam; unused until the image upgrade.


def _compact_params(element: dict[str, Any]) -> dict[str, float] | None:
    """This element's own numeric parameters — without these the model has no way to
    judge density/compensation/stitch-length per shape and has to guess."""
    params = element.get("params") or {}
    out: dict[str, float] = {}
    for key in ("row_spacing_mm", "pull_compensation_mm", "expand_mm"):
        value = _parse_num(params.get(key))
        if value is not None:
            out[key] = value
    stitch_length = _collect_stitch_length_mm(params)
    if stitch_length is not None:
        out["stitch_length_mm"] = stitch_length
    return out or None


def _compact_elements(design_report: dict[str, Any]) -> list[dict[str, Any]]:
    elements = _valid_elements(design_report)
    compact: list[dict[str, Any]] = []
    for el in elements[:MAX_ELEMENTS_FOR_REVIEW]:
        entry: dict[str, Any] = {
            "id": el.get("id"),
            "stitch_type": el.get("stitch_type"),
            "min_width_mm": el.get("min_dimension_mm"),
            "node_count": el.get("node_count"),
            # Real coordinates so the model can judge layout/overlap instead of guessing
            # from stitch order alone (e.g. don't claim "stacked" shapes that don't touch).
            "bbox_mm": el.get("bounding_box"),
        }
        params = _compact_params(el)
        if params:
            entry["params"] = params
        compact.append(entry)
    return compact


def _existing_findings(rules_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"id": i.get("id"), "title": i.get("title")}
        for i in (rules_payload.get("issues") or [])
        if isinstance(i, dict)
    ]


def build_review_messages(inputs: AIReviewInputs) -> list[BaseMessage]:
    dr = inputs.design_report
    summary = dr.get("summary") or {}
    structure = dr.get("structure") or {}
    elements = _compact_elements(dr)
    total_elements = len(_valid_elements(dr))
    payload = {
        "fabric": inputs.fabric or "unknown",
        "garment": (dr.get("meta") or {}).get("garment_type"),
        "summary": {
            "element_count": summary.get("element_count"),
            "stitch_types": structure.get("stitch_types"),
        },
        "elements": elements,
        # True if the design has more shapes than were included above — tells the model
        # not to make claims that require having seen every element.
        "elements_truncated": total_elements > len(elements),
        "already_reported": _existing_findings(inputs.rules_payload),
    }
    human = (
        "Design data:\n"
        f"{json.dumps(payload, indent=2, default=str)}\n\n"
        "Relevant documentation:\n"
        f"{inputs.rag_context}\n\n"
        "Return the JSON array of judgment findings now."
    )

    content: Any = human
    if inputs.image is not None:
        # Vision-ready: a provided image is sent as a multimodal content list. The exact
        # block shape is finalized when the image upgrade lands; unused for now.
        b64 = base64.b64encode(inputs.image).decode("ascii")
        content = [
            {"type": "text", "text": human},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]

    return [
        SystemMessage(content=load_ai_review_prompt()),
        HumanMessage(content=content),
    ]


def _message_text(content: Any) -> str:
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content or "")


def _extract_json_array(text: str) -> list[Any] | None:
    """Extract a JSON array from the LLM output, tolerant of fences and truncation."""
    text = text.strip()
    # Drop a leading ```json / ``` fence and any trailing fence (handles a missing close).
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    start = text.find("[")
    if start == -1:
        return None
    body = text[start:]
    try:
        data = json.loads(body)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Salvage a truncated array: keep objects up to the last complete "}".
    last_obj = body.rfind("}")
    if last_obj != -1:
        try:
            data = json.loads(body[: last_obj + 1] + "]")
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return None


def _focus_bbox(design_report: dict[str, Any], element_ids: list[str]):
    ids = set(element_ids)
    boxes = [_element_bbox(el) for el in _valid_elements(design_report) if el.get("id") in ids]
    return _union_bbox([b for b in boxes if b is not None])


# --------------------------------------------------------------------------------- #
# Trust guards. The prompt tells the model not to repeat deterministic findings and
# to ground claims in the data — it doesn't always listen. These check the claim
# against the actual design instead of trusting the text.
# --------------------------------------------------------------------------------- #

_DEDUP_STOPWORDS = {"too", "missing", "present", "high", "low", "short", "long", "count", "risk"}


def _topic_keywords(rule_id: str) -> set[str]:
    return {w for w in rule_id.lower().split("_") if w and len(w) > 2 and w not in _DEDUP_STOPWORDS}


def _is_duplicate_of_existing(text: str, existing_issues: list[dict[str, Any]]) -> bool:
    """True if `text` is topically the same claim as an already-fired deterministic issue.

    The prompt already tells the model the id/title of everything the rules found and
    says not to repeat it — this is the code-level backstop for when it does anyway.
    """
    for issue in existing_issues:
        if not isinstance(issue, dict):
            continue
        keywords = _topic_keywords(str(issue.get("id") or ""))
        if not keywords:
            continue
        hits = sum(1 for kw in keywords if kw in text)
        if hits == len(keywords) or hits >= 2:
            return True
    return False


# Topics with an objective, per-element ground truth we can check the claim against.
# All keywords must appear in the finding's text to trigger verification — keeps this
# from firing on unrelated findings that happen to share one word.
_VERIFIABLE_TOPICS: list[tuple[frozenset[str], list[str]]] = [
    (frozenset({"row", "spacing"}), ["row_spacing_too_low", "row_spacing_too_high"]),
    (frozenset({"density"}), ["row_spacing_too_low", "row_spacing_too_high", "extreme_density"]),
    (frozenset({"pull", "compensation"}), ["pull_compensation_missing"]),
    (frozenset({"stitch", "length"}), ["stitch_length_too_short", "stitch_length_too_long"]),
    (frozenset({"narrow"}), ["narrow_geometry_stitch_mismatch", "fill_on_narrow_path"]),
]


def _verify_element_ids(
    element_ids: list[str], text: str, design_report: dict[str, Any]
) -> list[str] | None:
    """For a checkable topic, keep only element_ids the real per-element data agrees
    with. Returns None ("drop this finding") when none of the named shapes actually
    exhibit the claimed problem. Returns element_ids unchanged for topics we have no
    ground truth for — most judgment findings (legibility, layout, routing, etc).
    """
    if not element_ids:
        return element_ids
    for keywords, rule_ids in _VERIFIABLE_TOPICS:
        if not all(kw in text for kw in keywords):
            continue
        verified: set[str] = set()
        for rule_id in rule_ids:
            verified.update(resolve_issue_targets(rule_id, design_report)["element_ids"])
        kept = [eid for eid in element_ids if eid in verified]
        return kept or None
    return element_ids


MAX_DETAIL_CHARS = 220


def _clip_text(text: str, limit: int = MAX_DETAIL_CHARS) -> str:
    """Word-boundary truncation. The prompt asks for 1-2 sentences but doesn't always
    get followed — this keeps every card scannable regardless, instead of relying on
    the instruction alone (same reasoning as the dedup/verification guards above)."""
    text = text.strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].rstrip(".,;: ")
    return f"{clipped}…"


_LAYOUT_CLAIM_WORDS = {"stack", "stacked", "stacking", "overlap", "overlapping", "layer", "layered"}


def _bboxes_overlap(a: dict[str, float], b: dict[str, float]) -> bool:
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


def _claims_unverified_overlap(
    text: str, element_ids: list[str], design_report: dict[str, Any]
) -> bool:
    """True if the finding claims shapes are stacked/overlapping/layered but their
    real bounding boxes don't actually touch — catches an invented spatial relationship."""
    if len(element_ids) < 2 or not any(word in text for word in _LAYOUT_CLAIM_WORDS):
        return False
    ids = set(element_ids)
    boxes = [
        _element_bbox(el) for el in _valid_elements(design_report) if str(el.get("id")) in ids
    ]
    boxes = [b for b in boxes if b is not None]
    if len(boxes) < 2:
        return False
    return not any(
        _bboxes_overlap(boxes[i], boxes[j])
        for i in range(len(boxes))
        for j in range(i + 1, len(boxes))
    )


def _sources_from_refs(
    refs: Any, chunks: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Map the LLM's 1-based [n] chunk references to deduped Source dicts."""
    if not chunks or not isinstance(refs, list):
        return []
    out: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for ref in refs:
        try:
            idx = int(ref) - 1  # format_context numbers chunks from 1
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(chunks):
            continue
        meta = chunks[idx].get("metadata") or {}
        # LlamaCloud metadata (e.g. page_label) can be non-string; coerce to str | None so
        # it validates against the Source schema.
        def _s(value: Any) -> str | None:
            return str(value) if value is not None else None

        key = (meta.get("source_file"), meta.get("section_title"))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "source_file": _s(meta.get("source_file")),
                "source_url": _s(meta.get("source_url")),
                "section_title": _s(meta.get("section_title")),
            }
        )
    return out


def parse_findings(
    text: str,
    design_report: dict[str, Any],
    chunks: list[dict[str, Any]] | None = None,
    existing_issues: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Robustly parse the LLM JSON into validated issue dicts (source='ai').

    `existing_issues` (the deterministic rule findings already reported to the model)
    lets this drop AI findings that duplicate them despite the prompt's instruction not
    to, and re-checks quantifiable claims (density, pull comp, stitch length, narrow
    width, claimed overlap) against the real per-element data before trusting them.
    """
    raw = _extract_json_array(text)
    if not raw:
        return []
    valid_ids = {str(el.get("id")) for el in _valid_elements(design_report) if el.get("id")}
    findings: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        capability = str(item.get("capability", "")).lower().strip()
        if capability not in _ALLOWED_CAPS:
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        detail = str(item.get("detail") or "").strip()
        text_lower = f"{title} {detail}".lower()
        if existing_issues and _is_duplicate_of_existing(text_lower, existing_issues):
            continue
        severity = str(item.get("severity", "medium")).lower().strip()
        if severity not in _ALLOWED_SEV:
            severity = "medium"
        try:
            confidence = min(1.0, max(0.0, float(item.get("confidence"))))
        except (TypeError, ValueError):
            confidence = 0.7
        element_ids = [str(x) for x in (item.get("element_ids") or []) if str(x) in valid_ids]
        if _claims_unverified_overlap(text_lower, element_ids, design_report):
            continue
        verified_ids = _verify_element_ids(element_ids, text_lower, design_report)
        if verified_ids is None:
            continue
        element_ids = verified_ids
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:32] or "finding"
        findings.append(
            {
                "id": f"ai_{slug}_{idx}",
                "category": "ai",
                "severity": severity,
                "title": title,
                "detail": _clip_text(detail),
                "suggested_action": _clip_text(str(item.get("suggested_action") or "").strip()),
                "source": "ai",
                "confidence": confidence,
                "capability": capability,
                "element_ids": element_ids,
                "focus_bbox": _focus_bbox(design_report, element_ids) if element_ids else None,
                "instances": build_instances(design_report, element_ids) if element_ids else [],
                "fix": None,
                "sources": _sources_from_refs(item.get("source_refs"), chunks),
            }
        )
        if len(findings) >= MAX_FINDINGS:
            break
    return findings


def _review_query(
    design_report: dict[str, Any], fabric: str | None, rules_payload: dict[str, Any]
) -> str:
    structure = design_report.get("structure") or {}
    stitch_types = ", ".join(structure.get("stitch_types") or []) or "embroidery"
    issue_titles = ", ".join(
        str(i.get("title"))
        for i in (rules_payload.get("issues") or [])[:5]
        if isinstance(i, dict) and i.get("title")
    )
    focus = issue_titles or "underlay, density, stitch type choice, small text, satin width"
    return f"embroidery digitizing best practices for {stitch_types} on {fabric or 'fabric'}: {focus}"


async def run_ai_review(
    design_report: dict[str, Any],
    rules_payload: dict[str, Any],
    svg_bytes: bytes | None = None,
) -> list[dict[str, Any]]:
    """Run the LLM review; return validated 🟡/🔵 findings (or [] if no LLM / on failure).

    When `svg_bytes` is given and a renderer is available, a PNG of the design is sent to
    the model so it can also reason about visual issues (small text, layout, aesthetics).
    """
    if not settings.has_llm:
        return []
    fabric = (design_report.get("physical") or {}).get("fabric_type")
    chunks: list[dict[str, Any]] = []
    try:
        rag = await rag_service.retrieve(_review_query(design_report, fabric, rules_payload))
        chunks = rag.chunks
        rag_context = rag_service.format_context(chunks)
    except Exception as exc:  # noqa: BLE001 - RAG is best-effort grounding
        logger.warning("ai_review_rag_failed", error=str(exc))
        rag_context = "No documentation retrieved."

    image: bytes | None = None
    if svg_bytes:
        image = await asyncio.to_thread(render_svg_to_png, svg_bytes)

    inputs = AIReviewInputs(
        design_report=design_report,
        fabric=fabric,
        rules_payload=rules_payload,
        rag_context=rag_context,
        image=image,
    )
    existing_issues = [i for i in (rules_payload.get("issues") or []) if isinstance(i, dict)]
    messages = build_review_messages(inputs)

    # Without extended thinking / enforced JSON mode, "return a JSON array" is a soft
    # prompt instruction the model doesn't always follow - it can come back with prose,
    # a truncated array, or otherwise unparseable text with zero API-level error. That's
    # indistinguishable from "the model genuinely found nothing" unless logged, so log
    # the raw text on an empty result, and retry once before accepting "no findings".
    for attempt in (1, 2):
        try:
            response = await llm_service.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - never let a review failure break the flow
            logger.warning("ai_review_llm_failed", attempt=attempt, error=str(exc))
            return []
        text = _message_text(response.content)
        findings = parse_findings(text, design_report, chunks, existing_issues)
        if findings:
            return findings
        logger.warning(
            "ai_review_empty_result", attempt=attempt, response_preview=text[:500]
        )
    return []
