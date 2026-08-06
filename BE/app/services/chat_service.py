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
from app.services.issue_element_mapper import enrich_rule_engine_payload
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
    selected_finding_id: str | None = None,
) -> tuple[str, list[dict[str, Any]], str, str, dict[str, Any], dict[str, Any]]:
    accumulated = extract_context(user_message, history)
    stored = design_report.get("session_context")
    if isinstance(stored, dict):
        from app.services.context_extractor import SessionContext

        accumulated = SessionContext.from_dict(stored).merge(accumulated)

    apply_context_to_report(design_report, accumulated)
    has_design = has_design_uploaded(design_report)
    rules_result = run_rule_engine(design_report) if has_design else _chat_only_rules_payload()
    if has_design:
        rules_result = enrich_rule_engine_payload(design_report, rules_result)
        design_report["cached_rule_engine"] = rules_result

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
    fabric_known = bool((design_report.get("physical") or {}).get("fabric_type"))

    # The finding the user currently has selected/highlighted in the UI, if any — resolved by id
    # so the model can answer "how do I fix this" without asking which finding "this" is.
    selected_finding: dict[str, Any] | None = None
    if selected_finding_id:
        # The FE also generates per-shape instance ids as "{issue_id}::{element_id}" when the
        # user drills into one shape within a finding — fall back to the parent finding for those.
        parent_id = selected_finding_id.split("::", 1)[0]
        for issue in rules_result.get("issues") or []:
            issue_id = issue.get("id")
            if issue_id == selected_finding_id or issue_id == parent_id:
                selected_finding = issue
                break

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
    elif wants_preflight:
        flow_instruction = (
            "\n\nThe user requested a preflight check. Use the formal preflight section structure."
        )
    elif describes_symptom:
        flow_instruction = (
            "\n\nThe user described a stitch-out symptom. Apply diagnosis discipline: synthesize the "
            "rule_engine issues that match this symptom (plus RAG docs) into the primary root cause, not "
            "a list of every finding that fired. Keep specific rule/element IDs to an optional closing "
            "technical note. Do not ask about fabric/garment/hoop first, they don't change this diagnosis. "
            "Ask at most one follow-up question, and only if the answer would change the diagnosis or "
            "recommendation. Skip context_gaps."
        )
    else:
        # Reaching here means has_design is True (the `not has_design` branch above already
        # caught the only case with no review) — so a review has ALREADY run automatically on
        # upload, regardless of chat turn count. Onboarding questions ("what are you trying to
        # achieve", "what garment is this", "run a preflight check") are never appropriate here:
        # the findings, and often the fabric/selected finding too, already exist below.
        selected_bit = " and the finding they currently have highlighted" if selected_finding else ""
        if is_first_user_turn and not fabric_known:
            flow_instruction = (
                "\n\nThis is the user's first chat message, but a review already ran automatically "
                "on upload — rule_engine_findings.issues and the verdict already exist below. Do NOT "
                "ask what the user is trying to achieve or offer to run a preflight/another review. "
                "Answer their actual question directly using the findings" + selected_bit + ". "
                "Fabric is not set yet — only if the answer would genuinely differ by fabric, ask one "
                "short fabric question alongside your answer, not instead of it."
            )
        else:
            flow_instruction = (
                "\n\nA design review has already completed. Its findings" + selected_bit
                + (", and the fabric already set (see design report)" if fabric_known else "")
                + " are known context below. Treat this as the primary context: answer the user's "
                "question directly using it. Never ask onboarding questions (what are you trying to "
                "achieve, what garment is this, run a preflight/another review) — a review already "
                "ran. Never ask for fabric, garment, or which finding/objects are affected if that "
                "is already present below. Only ask a follow-up if the answer would genuinely change "
                "depending on something still missing."
            )

    messages: list = [
        SystemMessage(content=f"{system_prompt}\n\n{rag_instruction}{flow_instruction}")
    ]

    llm_rules = {
        **rules_result,
        "issues": rules_result.get("issues") or [],
        "context_gaps": rules_result.get("context_gaps") or [],
    }

    selected_finding_block = (
        f"Currently selected/highlighted finding (the user is looking at this in the UI right now — "
        f'when they say "this"/"it" they mean this finding unless context clearly says otherwise; '
        f"answer about it directly first, then optionally note any assumptions):\n"
        f"{json.dumps(selected_finding, indent=2)}\n\n"
        if selected_finding
        else ""
    )
    context_block = (
        f"Design uploaded: {has_design}\n"
        f"{selected_finding_block}"
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
