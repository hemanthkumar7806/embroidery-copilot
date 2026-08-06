"""Regression tests for chat flow-instruction branch precedence."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from app.services import chat_service
from app.services.rag import RagResult


def _design_report() -> dict:
    return {
        "summary": {"element_count": 59},
        "session_context": {"fabric_type": "cotton"},
    }


def _run_generate_chat_reply(
    user_message: str,
    design_report: dict | None = None,
    rules_result: dict | None = None,
    selected_finding_id: str | None = None,
) -> tuple[str, str]:
    """Invoke generate_chat_reply with rag/llm mocked.

    Returns (system_prompt, context_block) — the two messages sent to the LLM.
    """
    captured_messages: dict = {}

    async def fake_invoke(messages):
        captured_messages["messages"] = messages
        return AIMessage(content="stubbed reply")

    patches = [
        patch.object(
            chat_service.rag_service,
            "retrieve",
            new=AsyncMock(return_value=RagResult(status="ok", chunks=[])),
        ),
        patch.object(chat_service.llm_service, "invoke", new=fake_invoke),
        patch.object(chat_service.settings, "LLM_PROVIDER", "bedrock"),
    ]
    if rules_result is not None:
        patches.append(patch.object(chat_service, "run_rule_engine", return_value=rules_result))

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        asyncio.run(
            chat_service.generate_chat_reply(
                design_report=design_report if design_report is not None else _design_report(),
                history=[],
                user_message=user_message,
                selected_finding_id=selected_finding_id,
            )
        )

    messages = captured_messages["messages"]
    return messages[0].content, messages[1].content


def test_first_message_with_symptom_leads_with_diagnosis_not_garment_question():
    """A first-turn freeze/hang report must route to the symptom branch, not the
    generic first-turn onboarding branch, even though both conditions
    (`is_first_user_turn` and `describes_symptom`) are simultaneously true.
    """
    system_prompt, _ = _run_generate_chat_reply(
        "svg file passes troubleshoot but won't stitch out. If I try to view a "
        "stitch plan preview, run the simulator, or save as .PES, inkstitch "
        "freezes up completely."
    )
    system_prompt = system_prompt.lower()

    assert "synthesize the rule_engine issues" in system_prompt
    # The old per-turn instruction that caused the reported bug — must never be selected
    # once the symptom branch (or, below, the "review already completed" branch) applies.
    assert "ask clarifying questions (intent" not in system_prompt


def test_review_already_completed_skips_onboarding_when_fabric_known():
    """Regression for the reported bug: a review runs automatically on upload, so even
    a genuinely-first chat message must never ask onboarding questions once a
    design/fabric is already known — it must treat the review as primary context instead.
    """
    system_prompt, _ = _run_generate_chat_reply(
        "Hi, I just uploaded my design, what do you think?"
    )
    system_prompt = system_prompt.lower()

    assert "design review has already completed" in system_prompt
    assert "never ask onboarding questions" in system_prompt
    # The exact old per-turn instruction ("Ask clarifying questions (intent + fabric/garment)")
    # must be gone — that's the literal bug: it fired even though a review already existed.
    assert "ask clarifying questions (intent" not in system_prompt


def test_first_message_no_fabric_may_ask_fabric_only_not_full_onboarding():
    """First turn, design uploaded, fabric genuinely unset: at most a fabric question,
    never the old full onboarding instruction ("Ask clarifying questions (intent + ...").
    """
    report = {"summary": {"element_count": 59}}  # no session_context / fabric at all
    system_prompt, _ = _run_generate_chat_reply(
        "Hi, I just uploaded my design, what do you think?", design_report=report
    )
    system_prompt = system_prompt.lower()

    assert "fabric is not set yet" in system_prompt
    assert "ask clarifying questions (intent" not in system_prompt


def test_no_design_at_all_still_gets_true_onboarding():
    """The genuine onboarding case — no SVG uploaded yet, nothing to review — is untouched."""
    report = {"summary": {"element_count": 0}}
    system_prompt, _ = _run_generate_chat_reply("hi", design_report=report)
    system_prompt = system_prompt.lower()

    assert "no svg is uploaded" in system_prompt


def test_selected_finding_is_injected_into_context_and_answered_first():
    report = _design_report()
    rules = {
        "issues": [{"id": "row_spacing_too_low", "title": "Row spacing too low", "severity": "high"}],
        "context_gaps": [],
        "decision": {"status": "CAUTION"},
    }
    _, context_block = _run_generate_chat_reply(
        "How should I fix this for cotton?",
        design_report=report,
        rules_result=rules,
        selected_finding_id="row_spacing_too_low",
    )

    assert "Currently selected/highlighted finding" in context_block
    assert "row_spacing_too_low" in context_block


def test_selected_finding_resolves_per_shape_instance_id_to_parent():
    """FE sends "{issue_id}::{element_id}" for a single shape drilled into within a
    finding — the backend must still resolve it back to the parent finding."""
    report = _design_report()
    rules = {
        "issues": [{"id": "row_spacing_too_low", "title": "Row spacing too low", "severity": "high"}],
        "context_gaps": [],
        "decision": {"status": "CAUTION"},
    }
    _, context_block = _run_generate_chat_reply(
        "How should I fix this?",
        design_report=report,
        rules_result=rules,
        selected_finding_id="row_spacing_too_low::path94-1_5868",
    )

    assert "Currently selected/highlighted finding" in context_block
    assert "row_spacing_too_low" in context_block


def test_unmatched_selected_finding_id_does_not_crash_or_inject_block():
    report = _design_report()
    rules = {"issues": [], "context_gaps": [], "decision": {"status": "SAFE_TO_TEST"}}
    _, context_block = _run_generate_chat_reply(
        "How do I fix this?",
        design_report=report,
        rules_result=rules,
        selected_finding_id="nonexistent_id",
    )

    assert "Currently selected/highlighted finding" not in context_block
