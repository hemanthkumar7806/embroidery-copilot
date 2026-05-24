"""Prompt loaders for preflight and chat."""

from pathlib import Path


def _read_prompt(name: str) -> str:
    path = Path(__file__).parent / name
    return path.read_text(encoding="utf-8")


def load_preflight_prompt() -> str:
    return _read_prompt("preflight.md")


def load_chat_prompt() -> str:
    return _read_prompt("chat.md")
