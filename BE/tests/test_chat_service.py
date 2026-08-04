"""Regression tests for chat flow-instruction branch precedence."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from app.services import chat_service
from app.services.rag import RagResult


def _design_report() -> dict:
    return {
        "summary": {"element_count": 59},
        "session_context": {"fabric_type": "cotton"},
    }


def _run_generate_chat_reply(user_message: str) -> str:
    """Invoke generate_chat_reply with rag/llm mocked, return the system prompt sent to the LLM."""
    captured_messages: dict = {}

    async def fake_invoke(messages):
        captured_messages["messages"] = messages
        return AIMessage(content="stubbed reply")

    with (
        patch.object(
            chat_service.rag_service,
            "retrieve",
            new=AsyncMock(return_value=RagResult(status="ok", chunks=[])),
        ),
        patch.object(chat_service.llm_service, "invoke", new=fake_invoke),
        patch.object(chat_service.settings, "LLM_PROVIDER", "bedrock"),
    ):
        asyncio.run(
            chat_service.generate_chat_reply(
                design_report=_design_report(),
                history=[],
                user_message=user_message,
            )
        )

    return captured_messages["messages"][0].content


def test_first_message_with_symptom_leads_with_diagnosis_not_garment_question():
    """A first-turn freeze/hang report must route to the symptom branch, not the
    generic first-turn clarifying-question branch, even though both conditions
    (`is_first_user_turn` and `describes_symptom`) are simultaneously true.
    """
    system_prompt = _run_generate_chat_reply(
        "svg file passes troubleshoot but won't stitch out. If I try to view a "
        "stitch plan preview, run the simulator, or save as .PES, inkstitch "
        "freezes up completely."
    ).lower()

    assert "synthesize the rule_engine issues" in system_prompt
    assert "first message after the welcome" not in system_prompt


def test_first_message_without_symptom_asks_clarifying_questions():
    system_prompt = _run_generate_chat_reply(
        "Hi, I just uploaded my design, what do you think?"
    ).lower()

    assert "first message after the welcome" in system_prompt
