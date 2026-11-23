"""Slim LLM service with retries for the beta backend.

LLM clients are created lazily on first chat call so cold starts can serve
/health (and SVG upload) without waiting on Gemini/OpenAI SDK init.
"""

from typing import List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logging import logger

# Newer Claude generations (Sonnet 5, Opus 5, Fable 5, and Opus 4.7/4.8
# before them) remove sampling params entirely - passing a non-default
# `temperature` 400s. Thinking is on by default for these with no
# `thinking`/`budget_tokens` param to configure, and thinking tokens count
# against MAX_TOKENS, so give them more output headroom than the shared
# default assumes.
_NO_SAMPLING_OVERRIDE_MODELS = {
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-fable-5",
    "claude-opus-4-7",
    "claude-opus-4-8",
}
_THINKING_MIN_MAX_TOKENS = 16000


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
            anthropic_kwargs = dict(common)
            if name in _NO_SAMPLING_OVERRIDE_MODELS:
                anthropic_kwargs.pop("temperature", None)
                anthropic_kwargs["max_tokens"] = max(
                    anthropic_kwargs["max_tokens"], _THINKING_MIN_MAX_TOKENS
                )
            return ChatAnthropic(
                model=name,
                api_key=settings.ANTHROPIC_API_KEY,
                **anthropic_kwargs,
            )
        if settings.LLM_PROVIDER == "groq":
            return ChatOpenAI(
                model=name,
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
                **common,
            )
        if settings.LLM_PROVIDER == "openrouter":
            # OpenRouter proxies real Anthropic models but via an
            # OpenAI-compatible endpoint - it does NOT accept Anthropic's
            # native `thinking` param, so extended thinking stays off
            # (cheaper: no thinking tokens billed as output) unless
            # OPENROUTER_REASONING_EFFORT is explicitly set.
            openrouter_kwargs = dict(common)
            if settings.OPENROUTER_REASONING_EFFORT:
                openrouter_kwargs["extra_body"] = {
                    "reasoning": {"effort": settings.OPENROUTER_REASONING_EFFORT}
                }
            return ChatOpenAI(
                model=name,
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                **openrouter_kwargs,
            )
        if settings.LLM_PROVIDER == "gemini":
            return ChatGoogleGenerativeAI(
                model=name,
                google_api_key=settings.GEMINI_API_KEY,
                **common,
            )
        if settings.LLM_PROVIDER == "bedrock":
            # Imported lazily so the dependency is only needed when Bedrock is used.
            from langchain_aws import ChatBedrockConverse

            return ChatBedrockConverse(
                model=name,
                region_name=settings.AWS_REGION,
                **common,
            )
        return ChatOpenAI(
            model=name,
            api_key=settings.OPENAI_API_KEY,
            **common,
        )


class LLMService:
    """Single-model LLM caller; initializes the client on first use."""

    def __init__(self) -> None:
        self._llm: Optional[BaseChatModel] = None

    def _ensure_llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = LLMRegistry.get()
            logger.info(
                "llm_service_initialized",
                model=settings.DEFAULT_LLM_MODEL,
                provider=settings.LLM_PROVIDER,
            )
        return self._llm

    async def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        return await self._ensure_llm().ainvoke(messages)


llm_service = LLMService()
