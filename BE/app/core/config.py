"""Minimal configuration for the anonymous beta backend."""

import os
from pathlib import Path

from dotenv import load_dotenv

_BE_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_BE_ROOT / ".env")


def _parse_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    value = value.strip().strip("\"'")
    if "," not in value:
        return [value]
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Inkscape AI Beta")
    VERSION: str = "0.2.0"
    DESCRIPTION: str = "Anonymous SVG review and chat API for investor beta"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

    ALLOWED_ORIGINS: list[str] = _parse_list(
        os.getenv("ALLOWED_ORIGINS"),
        ["http://localhost:5173", "http://localhost:8000"],
    )

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "")
    DEFAULT_LLM_TEMPERATURE: float = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    MAX_LLM_CALL_RETRIES: int = int(os.getenv("MAX_LLM_CALL_RETRIES", "3"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    DOCS_DIR: Path = Path(os.getenv("DOCS_DIR", str(_BE_ROOT.parent / "docs")))
    SESSION_TTL_DAYS: int = int(os.getenv("SESSION_TTL_DAYS", "7"))
    MAX_SVG_BYTES: int = int(os.getenv("MAX_SVG_BYTES", str(5 * 1024 * 1024)))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "console")

    CHROMA_COLLECTION: str = "embroidery_docs"

    def __init__(self) -> None:
        if not self.DEFAULT_LLM_MODEL:
            defaults = {
                "openai": "gpt-4o-mini",
                "gemini": "gemini-2.5-flash",
                "anthropic": "claude-3-5-sonnet-20241022",
                "groq": "llama-3.1-8b-instant",
            }
            self.DEFAULT_LLM_MODEL = defaults.get(self.LLM_PROVIDER, "gpt-4o-mini")

        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "svgs").mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "chroma").mkdir(parents=True, exist_ok=True)

    @property
    def sqlite_path(self) -> Path:
        return self.DATA_DIR / "app.db"

    @property
    def chroma_path(self) -> Path:
        return self.DATA_DIR / "chroma"

    @property
    def has_llm(self) -> bool:
        if self.LLM_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        if self.LLM_PROVIDER == "groq":
            return bool(self.GROQ_API_KEY)
        if self.LLM_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY)
        return bool(self.OPENAI_API_KEY)

    @property
    def has_embeddings(self) -> bool:
        return bool(self.OPENAI_API_KEY)


settings = Settings()
