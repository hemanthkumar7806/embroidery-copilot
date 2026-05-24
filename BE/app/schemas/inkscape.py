"""Schemas for Inkscape bridge: user message in, structured tool call out."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class InkscapeActionRequest(BaseModel):
    """Request body for POST /inkscape/ask."""

    message: str = Field(
        ..., min_length=1, max_length=500, description="User request in natural language"
    )


class InkscapeActionResponse(BaseModel):
    """
    Structured tool call returned by LLM and stored for the extension.
    Extension executes only known tools with validated params; no hardcoded intents.
    """

    tool: str = Field(
        ...,
        description="Tool name: set_style, set_attribute, apply_transform, delete_objects, or unsupported",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool parameters (e.g. property/value for set_style, type/degrees for apply_transform)",
    )
    message: Optional[str] = Field(
        default=None,
        description="When tool is unsupported, short user-friendly reason",
    )
