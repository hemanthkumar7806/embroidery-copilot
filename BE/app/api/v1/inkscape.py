"""Inkscape bridge API: store/retrieve actions for the extension (no auth)."""

import json
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.prompts import load_inkscape_action_prompt
from app.schemas.inkscape import InkscapeActionRequest, InkscapeActionResponse
from app.services.llm import LLMRegistry

router = APIRouter()

LAST_ACTION: Optional[dict[str, Any]] = None


def _parse_json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)


@router.post("/ask", response_model=InkscapeActionResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("inkscape", ["60 per minute"])[0])
async def ask(request: Request, body: InkscapeActionRequest) -> InkscapeActionResponse:
    global LAST_ACTION
    try:
        llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
        system_prompt = load_inkscape_action_prompt()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=body.message.strip()),
        ]
        if settings.LLM_PROVIDER == "groq":
            raw = await llm.ainvoke(messages)
            content = raw.content
            if isinstance(content, list):
                content = "".join(
                    b.get("text", b) if isinstance(b, dict) else str(b) for b in content
                )
            content = content or "{}"
            data = _parse_json_from_text(content)
            result = InkscapeActionResponse(
                tool=data.get("tool", data.get("action", "unsupported")),
                params=data.get("params") or {},
                message=data.get("message"),
            )
        else:
            try:
                structured_llm = llm.with_structured_output(InkscapeActionResponse)
                result = await structured_llm.ainvoke(messages)
            except Exception as e:
                if "json_schema" in str(e).lower() or "response_format" in str(e).lower():
                    raw = await llm.ainvoke(messages)
                    content = getattr(raw, "content", "") or "{}"
                    if isinstance(content, list):
                        content = "".join(
                            b.get("text", b) if isinstance(b, dict) else str(b)
                            for b in content
                        )
                    data = _parse_json_from_text(content)
                    result = InkscapeActionResponse(
                        tool=data.get("tool", data.get("action", "unsupported")),
                        params=data.get("params") or {},
                        message=data.get("message"),
                    )
                else:
                    raise
        LAST_ACTION = result.model_dump()
        logger.info("inkscape_ask_stored", tool=result.tool)
        return result
    except json.JSONDecodeError as e:
        logger.warning("inkscape_ask_json_parse_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Model response was not valid JSON.")
    except Exception as e:
        logger.exception("inkscape_ask_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-action")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS.get("inkscape", ["60 per minute"])[0])
def get_action(request: Request, consume: bool = True) -> Optional[dict[str, Any]]:
    global LAST_ACTION
    action = LAST_ACTION
    if consume:
        LAST_ACTION = None
    if action:
        logger.info("inkscape_action_fetched", tool=action.get("tool"), consume=consume)
    return action
