"""Follow-up chat grounded in design report and RAG."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.core.prompts import load_chat_prompt
from app.models.session import Message
from app.services.llm import llm_service
from app.services.offline_fallback import build_offline_chat_reply
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


async def generate_chat_reply(
    design_report: dict[str, Any],
    history: list[Message],
    user_message: str,
) -> tuple[str, list[dict[str, Any]]]:
    chunks = rag_service.retrieve(user_message)
    if not settings.has_llm:
        return build_offline_chat_reply(design_report, user_message), chunks
    context = rag_service.format_context(chunks)
    system_prompt = load_chat_prompt()
    messages: list = [SystemMessage(content=system_prompt)]

    context_block = (
        f"Design report JSON:\n{json.dumps(design_report, indent=2)}\n\n"
        f"Retrieved documentation:\n{context}"
    )
    messages.append(HumanMessage(content=context_block))

    for item in history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))

    messages.append(HumanMessage(content=user_message))
    response = await llm_service.invoke(messages)
    return _message_content(response.content), chunks
