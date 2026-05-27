"""Follow-up chat grounded in design report and RAG."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.core.prompts import load_chat_prompt, load_preflight_prompt
from app.models.session import Message
from app.services.context_extractor import (
    apply_context_to_report,
    extract_context,
    has_design_uploaded,
    user_describes_symptom,
    user_requests_preflight,
)
from app.services.llm import llm_service
from app.services.offline_fallback import build_offline_chat_reply
from app.services.rag import rag_service
from app.services.rule_engine import run as run_rule_engine


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


def _user_turn_count(history: list[Message]) -> int:
    return sum(1 for item in history if item.role == "user")


def _chat_only_rules_payload() -> dict[str, Any]:
    return {
        "issues": [],
        "context_gaps": [],
        "decision": {"status": "N/A", "reason": "No design uploaded"},
        "note": (
            "No SVG file is loaded. Do NOT cite rule issue IDs or a stitch verdict. "
            "Answer from the user's described symptom and retrieved docs only."
        ),
    }


async def generate_chat_reply(
    design_report: dict[str, Any],
    history: list[Message],
    user_message: str,
) -> tuple[str, list[dict[str, Any]], str, str, dict[str, Any], dict[str, Any]]:
    accumulated = extract_context(user_message, history)
    stored = design_report.get("session_context")
    if isinstance(stored, dict):
        from app.services.context_extractor import SessionContext

        accumulated = SessionContext.from_dict(stored).merge(accumulated)

    apply_context_to_report(design_report, accumulated)
    has_design = has_design_uploaded(design_report)
    rules_result = run_rule_engine(design_report) if has_design else _chat_only_rules_payload()

    rag = await rag_service.retrieve(user_message)
    chunks = rag.chunks
    if not settings.has_llm:
        reply = build_offline_chat_reply(design_report, user_message)
        return reply, chunks, rag.status, rag.detail, rules_result, design_report

    context = rag_service.format_context(chunks)
    user_turns = _user_turn_count(history)
    wants_preflight = has_design and user_requests_preflight(user_message)
    describes_symptom = user_describes_symptom(accumulated)
    is_first_user_turn = user_turns == 0

    if wants_preflight:
        system_prompt = load_preflight_prompt()
    else:
        system_prompt = load_chat_prompt()

    rag_instruction = (
        "LlamaCloud documentation was retrieved for this turn. Base your answer primarily on those chunks."
        if rag.status == "ok"
        else (
            f"LlamaCloud documentation was NOT available (status={rag.status}). "
            f"Reason: {rag.detail or 'unknown'}. "
            "Say clearly that this answer is general guidance, not from the indexed doc library."
        )
    )

    flow_instruction = ""
    if not has_design:
        flow_instruction = (
            "\n\nNO SVG is uploaded (element_count is 0). "
            "Do NOT cite rule issue IDs, do NOT give SAFE_TO_TEST/CAUTION/FIX_BEFORE_STITCH. "
            "Answer from retrieved docs and the user's described problem. "
            "If they pasted a troubleshooting story, explain likely causes (complexity, narrow fills, "
            "too many nodes, wrong stitch type) and ask them to upload their SVG for a file-specific check."
        )
    elif is_first_user_turn and not wants_preflight:
        flow_instruction = (
            "\n\nThis is the user's FIRST message after the welcome. "
            "Ask clarifying questions (intent + fabric/garment). Do NOT output a full preflight checklist yet."
        )
    elif wants_preflight:
        flow_instruction = (
            "\n\nThe user requested a preflight check. Use the formal preflight section structure."
        )
    elif describes_symptom:
        flow_instruction = (
            "\n\nThe user described a stitch-out symptom. Troubleshoot conversationally using "
            "rule_engine issues that match the symptom and RAG docs. Skip context_gaps."
        )

    messages: list = [
        SystemMessage(content=f"{system_prompt}\n\n{rag_instruction}{flow_instruction}")
    ]

    llm_rules = {
        **rules_result,
        "issues": rules_result.get("issues") or [],
        "context_gaps": rules_result.get("context_gaps") or [],
    }

    context_block = (
        f"Design uploaded: {has_design}\n"
        f"Design report JSON:\n{json.dumps(design_report, indent=2)}\n\n"
        "Rule engine findings (cite issue IDs only when Design uploaded is true):\n"
        f"{json.dumps(llm_rules, indent=2)}\n\n"
        f"Retrieved documentation (LlamaCloud):\n{context}"
    )
    messages.append(HumanMessage(content=context_block))

    for item in history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))

    messages.append(HumanMessage(content=user_message))
    response = await llm_service.invoke(messages)
    return (
        _message_content(response.content),
        chunks,
        rag.status,
        rag.detail,
        rules_result,
        design_report,
    )
