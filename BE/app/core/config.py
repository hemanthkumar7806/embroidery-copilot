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


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


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
    AWS_REGION: str = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "")
    DEFAULT_LLM_TEMPERATURE: float = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
    MAX_LLM_CALL_RETRIES: int = int(os.getenv("MAX_LLM_CALL_RETRIES", "3"))

    LLAMA_CLOUD_API_KEY: str = os.getenv("LLAMA_CLOUD_API_KEY", "")
    LLAMA_CLOUD_PIPELINE_ID: str = os.getenv("LLAMA_CLOUD_PIPELINE_ID", "")
    LLAMA_CLOUD_PROJECT_ID: str = os.getenv("LLAMA_CLOUD_PROJECT_ID", "")
    LLAMA_CLOUD_RETRIEVAL_TOP_K: int = int(os.getenv("LLAMA_CLOUD_RETRIEVAL_TOP_K", "8"))
    LLAMA_CLOUD_ENABLE_RERANKING: bool = _parse_bool(
        os.getenv("LLAMA_CLOUD_ENABLE_RERANKING"), True
    )

    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    DOCS_DIR: Path = Path(os.getenv("DOCS_DIR", str(_BE_ROOT.parent / "docs")))
    SESSION_TTL_DAYS: int = int(os.getenv("SESSION_TTL_DAYS", "7"))
    MAX_SVG_BYTES: int = int(os.getenv("MAX_SVG_BYTES", str(5 * 1024 * 1024)))

    # Optional external database (e.g. Supabase Postgres). When empty, falls back
    # to the local SQLite file at DATA_DIR/app.db.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "").strip()

    # Analytics + admin dashboard
    ANALYTICS_ENABLED: bool = _parse_bool(os.getenv("ANALYTICS_ENABLED"), True)
    VISITOR_COOKIE_NAME: str = os.getenv("VISITOR_COOKIE_NAME", "vid").strip() or "vid"
    # Cookies default to Secure in production; disable automatically in DEBUG so
    # they work over plain http://localhost during development.
    COOKIE_SECURE: bool = _parse_bool(
        os.getenv("COOKIE_SECURE"), os.getenv("DEBUG", "true").lower() not in ("true", "1", "yes")
    )
    # Admin dashboard bearer token. When empty, admin endpoints are disabled.
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "").strip()

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "console")

    def __init__(self) -> None:
        if not self.DEFAULT_LLM_MODEL:
            defaults = {
                "openai": "gpt-4o-mini",
                "gemini": "gemini-2.5-flash",
                "anthropic": "claude-3-5-sonnet-20241022",
                "groq": "llama-3.1-8b-instant",
                "bedrock": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            }
            self.DEFAULT_LLM_MODEL = defaults.get(self.LLM_PROVIDER, "gpt-4o-mini")

        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "svgs").mkdir(parents=True, exist_ok=True)

    @property
    def sqlite_path(self) -> Path:
        return self.DATA_DIR / "app.db"

    @property
    def db_is_sqlite(self) -> bool:
        return not self.DATABASE_URL

    @property
    def resolved_database_url(self) -> str:
        """SQLAlchemy URL: external DATABASE_URL if set, else local SQLite."""
        if not self.DATABASE_URL:
            return f"sqlite:///{self.sqlite_path.as_posix()}"

        url = self.DATABASE_URL
        # SQLAlchemy needs an explicit driver; use psycopg (v3).
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        # Managed Postgres (Supabase) requires TLS.
        if "+psycopg" in url and "sslmode=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
        return url

    @property
    def has_llm(self) -> bool:
        if self.LLM_PROVIDER == "bedrock":
            return True
        if self.LLM_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        if self.LLM_PROVIDER == "groq":
            return bool(self.GROQ_API_KEY)
        if self.LLM_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY)
        return bool(self.OPENAI_API_KEY)

    @property
    def has_rag(self) -> bool:
        return bool(
            self.LLAMA_CLOUD_API_KEY
            and self.LLAMA_CLOUD_PIPELINE_ID
            and not self.rag_pipeline_misconfigured
        )

    @property
    def rag_pipeline_misconfigured(self) -> bool:
        """Project ID was mistakenly used as pipeline ID."""
        if not self.LLAMA_CLOUD_PIPELINE_ID or not self.LLAMA_CLOUD_PROJECT_ID:
            return False
        return self.LLAMA_CLOUD_PIPELINE_ID.strip() == self.LLAMA_CLOUD_PROJECT_ID.strip()


settings = Settings()
