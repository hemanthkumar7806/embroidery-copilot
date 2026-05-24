"""Slim LLM service with retries for the beta backend."""

from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logging import logger


class LLMRegistry:
    """Registry for the configured chat model."""

    @classmethod
    def get(cls, model_name: str | None = None, **kwargs) -> BaseChatModel:
        name = model_name or settings.DEFAULT_LLM_MODEL
        common = {
            "max_tokens": settings.MAX_TOKENS,
            "temperature": settings.DEFAULT_LLM_TEMPERATURE,
            **kwargs,
        }
        if settings.LLM_PROVIDER == "anthropic":
            return ChatAnthropic(
                model=name,
                api_key=settings.ANTHROPIC_API_KEY,
                **common,
            )
        if settings.LLM_PROVIDER == "groq":
            return ChatOpenAI(
                model=name,
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
                **common,
            )
        if settings.LLM_PROVIDER == "gemini":
            return ChatGoogleGenerativeAI(
                model=name,
                google_api_key=settings.GEMINI_API_KEY,
                **common,
            )
        return ChatOpenAI(
            model=name,
            api_key=settings.OPENAI_API_KEY,
            **common,
        )


class LLMService:
    """Single-model LLM caller with retry logic."""

    def __init__(self) -> None:
        self._llm = LLMRegistry.get()
        logger.info("llm_service_initialized", model=settings.DEFAULT_LLM_MODEL, provider=settings.LLM_PROVIDER)

    async def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        return await self._llm.ainvoke(messages)


llm_service = LLMService()
