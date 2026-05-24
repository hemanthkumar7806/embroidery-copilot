"""Generate the initial preflight report."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.prompts import load_preflight_prompt
from app.services.llm import llm_service
from app.services.offline_fallback import build_offline_preflight
from app.services.rag import rag_service


def _message_content(response_content: Any) -> str:
    if isinstance(response_content, list):
        parts = []
        for block in response_content:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(response_content or "")


def _build_retrieval_query(design_report: dict[str, Any]) -> str:
    summary = design_report.get("summary") or {}
    counts = summary.get("stitch_type_counts") or {}
    parts = [
        "Ink/Stitch embroidery preflight",
        f"elements {summary.get('element_count', 0)}",
        f"stitch types {counts}",
        f"hidden layers {summary.get('hidden_layer_count', 0)}",
        "trim spacing satin fill stabilizer",
    ]
    return " ".join(str(p) for p in parts if p)


async def generate_preflight(design_report: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    query = _build_retrieval_query(design_report)
    chunks = rag_service.retrieve(query)
    if not settings.has_llm:
        return build_offline_preflight(design_report), chunks
    context = rag_service.format_context(chunks)
    system_prompt = load_preflight_prompt()
    human_payload = (
        "Generate the initial preflight report for this uploaded design.\n\n"
        f"Design report JSON:\n{json.dumps(design_report, indent=2)}\n\n"
        f"Retrieved documentation:\n{context}"
    )
    response = await llm_service.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=human_payload)]
    )
    return _message_content(response.content), chunks
