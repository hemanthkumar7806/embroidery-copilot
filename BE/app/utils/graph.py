"""This file contains the graph utilities for the application."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.messages import trim_messages as _trim_messages

from app.core.config import settings
from app.core.logging import logger
from app.schemas import Message


def dump_messages(messages: list[Message]) -> list[dict]:
    """Dump the messages to a list of dictionaries.

    Args:
        messages (list[Message]): The messages to dump.

    Returns:
        list[dict]: The dumped messages.
    """
    return [message.model_dump() for message in messages]


def process_llm_response(response: BaseMessage) -> BaseMessage:
    """Process LLM response to handle structured content blocks (e.g., from GPT-5 models).

    GPT-5 models return content as a list of blocks like:
    [
        {'id': '...', 'summary': [], 'type': 'reasoning'},
        {'type': 'text', 'text': 'actual response'}
    ]

    This function extracts the actual text content from such structures.

    Args:
        response: The raw response from the LLM

    Returns:
        BaseMessage with processed content
    """
    if isinstance(response.content, list):
        # Extract text from content blocks
        text_parts = []
        for block in response.content:
            if isinstance(block, dict):
                # Handle text blocks
                if block.get("type") == "text" and "text" in block:
                    text_parts.append(block["text"])
                # Log reasoning blocks for debugging
                elif block.get("type") == "reasoning":
                    logger.debug(
                        "reasoning_block_received",
                        reasoning_id=block.get("id"),
                        has_summary=bool(block.get("summary")),
                    )
            elif isinstance(block, str):
                text_parts.append(block)

        # Join all text parts
        response.content = "".join(text_parts)
        logger.debug(
            "processed_structured_content",
            block_count=len(response.content) if isinstance(response.content, list) else 1,
            extracted_length=len(response.content) if isinstance(response.content, str) else 0,
        )

    return response


def _estimate_tokens(messages: list) -> int:
    """Estimate token count for messages (used when LLM does not support get_num_tokens_from_messages, e.g. Groq)."""
    total = 0
    for m in messages:
        content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total += len(part["text"])
    return max(1, total // 4)


def prepare_messages(messages: list[Message], llm: BaseChatModel, system_prompt: str) -> list[Message]:
    """Prepare the messages for the LLM.

    Args:
        messages (list[Message]): The messages to prepare.
        llm (BaseChatModel): The LLM to use.
        system_prompt (str): The system prompt to use.

    Returns:
        list[Message]: The prepared messages.
    """
    dumped = dump_messages(messages)
    # Groq and other non-OpenAI models don't implement get_num_tokens_from_messages; use estimate
    token_counter = (
        _estimate_tokens
        if settings.LLM_PROVIDER == "groq"
        else llm
    )
    try:
        trimmed_messages = _trim_messages(
            dumped,
            strategy="last",
            token_counter=token_counter,
            max_tokens=settings.MAX_TOKENS,
            start_on="human",
            include_system=False,
            allow_partial=False,
        )
    except NotImplementedError:
        logger.warning(
            "token_counting_not_implemented_using_estimate",
            provider=settings.LLM_PROVIDER,
            message_count=len(messages),
        )
        trimmed_messages = _trim_messages(
            dumped,
            strategy="last",
            token_counter=_estimate_tokens,
            max_tokens=settings.MAX_TOKENS,
            start_on="human",
            include_system=False,
            allow_partial=False,
        )
    except ValueError as e:
        # Handle unrecognized content blocks (e.g., reasoning blocks from GPT-5)
        if "Unrecognized content block type" in str(e):
            logger.warning(
                "token_counting_failed_skipping_trim",
                error=str(e),
                message_count=len(messages),
            )
            trimmed_messages = messages
        else:
            raise

    if trimmed_messages and isinstance(trimmed_messages[0], dict):
        trimmed_messages = [Message(**m) for m in trimmed_messages]
    return [Message(role="system", content=system_prompt)] + list(trimmed_messages)
