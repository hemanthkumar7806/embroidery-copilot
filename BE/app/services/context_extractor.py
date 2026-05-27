"""Extract fabric, garment, symptom, and hoop context from chat messages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.session import Message

FABRIC_KEYWORDS: dict[str, str] = {
    "cotton": "cotton",
    "knit": "knit",
    "jersey": "jersey",
    "pique": "pique",
    "fleece": "fleece",
    "sherpa": "sherpa",
    "terry": "terry",
    "denim": "denim",
    "twill": "twill",
    "leather": "leather",
    "silk": "silk",
    "polyester": "polyester",
    "lycra": "lycra",
    "spandex": "spandex",
    "stretch": "stretch",
    "poly": "polyester",
}

GARMENT_KEYWORDS: dict[str, str] = {
    "polo": "polo",
    "hoodie": "hoodie",
    "sweatshirt": "sweatshirt",
    "hat": "hat",
    "cap": "cap",
    "towel": "towel",
    "jacket": "jacket",
    "shirt": "shirt",
    "tee": "tee",
    "t-shirt": "tee",
    "tshirt": "tee",
}

SYMPTOM_PATTERNS: list[tuple[str, str]] = [
    (
        r"won'?t save|can't save|cannot save|freeze|freezes|frozen|hang|hanging|simulator|"
        r"stitch plan|won'?t stitch|un-?stitchable|inkstitch freeze",
        "save_or_simulator_freeze",
    ),
    (r"won'?t export|can't export|cannot export", "export_failure"),
    (r"pucker|puckering|wavy|distort|distortion|shrunk", "puckering_distortion"),
    (r"thread break|thread snap|shred|snaps|breaking thread", "thread_break"),
    (r"gap|gaps|showing through|coverage", "coverage_gaps"),
    (r"dense|too tight|overlap|bulky", "density_issue"),
    (r"narrow|too small|tiny", "narrow_geometry"),
]

HOOP_RE = re.compile(
    r"(\d{1,3}(?:\.\d+)?)\s*[x×]\s*(\d{1,3}(?:\.\d+)?)\s*(mm|cm|in|inches?|\")?",
    re.IGNORECASE,
)


@dataclass
class SessionContext:
    fabric_type: str | None = None
    garment_type: str | None = None
    symptom: str | None = None
    hoop_size_mm: dict[str, float] | None = None

    def merge(self, other: SessionContext) -> SessionContext:
        return SessionContext(
            fabric_type=other.fabric_type or self.fabric_type,
            garment_type=other.garment_type or self.garment_type,
            symptom=other.symptom or self.symptom,
            hoop_size_mm=other.hoop_size_mm or self.hoop_size_mm,
        )

    def to_dict(self) -> dict:
        return {
            "fabric_type": self.fabric_type,
            "garment_type": self.garment_type,
            "symptom": self.symptom,
            "hoop_size_mm": self.hoop_size_mm,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> SessionContext:
        if not data:
            return cls()
        hoop = data.get("hoop_size_mm")
        return cls(
            fabric_type=data.get("fabric_type"),
            garment_type=data.get("garment_type"),
            symptom=data.get("symptom"),
            hoop_size_mm=hoop if isinstance(hoop, dict) else None,
        )


def _normalize_hoop(w: float, h: float, unit: str | None) -> dict[str, float]:
    unit = (unit or "mm").lower().strip('"')
    if unit in ("in", "inch", "inches"):
        w, h = w * 25.4, h * 25.4
    elif unit == "cm":
        w, h = w * 10, h * 10
    return {"w": round(w, 2), "h": round(h, 2)}


def extract_from_text(text: str) -> SessionContext:
    lowered = text.lower()
    ctx = SessionContext()

    for keyword, fabric in FABRIC_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            ctx.fabric_type = fabric
            break

    for keyword, garment in GARMENT_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            ctx.garment_type = garment
            if garment == "polo" and not ctx.fabric_type:
                ctx.fabric_type = "cotton"
            if garment == "hoodie" and not ctx.fabric_type:
                ctx.fabric_type = "fleece"
            break

    for pattern, symptom in SYMPTOM_PATTERNS:
        if re.search(pattern, lowered):
            ctx.symptom = symptom
            break

    hoop_match = HOOP_RE.search(text)
    if hoop_match:
        ctx.hoop_size_mm = _normalize_hoop(
            float(hoop_match.group(1)),
            float(hoop_match.group(2)),
            hoop_match.group(3),
        )

    return ctx


def extract_context(user_message: str, history: list[Message] | None = None) -> SessionContext:
    ctx = extract_from_text(user_message)
    if history:
        for msg in history:
            if msg.role == "user":
                ctx = ctx.merge(extract_from_text(msg.content))
    return ctx


def apply_context_to_report(report: dict, ctx: SessionContext) -> dict:
    """Merge session context into a mutable design report dict."""
    session_ctx = SessionContext.from_dict(report.get("session_context")).merge(ctx)
    report["session_context"] = session_ctx.to_dict()

    if session_ctx.fabric_type:
        physical = report.setdefault("physical", {})
        if not physical.get("fabric_type"):
            physical["fabric_type"] = session_ctx.fabric_type
    if session_ctx.garment_type:
        meta = report.setdefault("meta", {})
        meta["garment_type"] = session_ctx.garment_type
    if session_ctx.symptom:
        meta = report.setdefault("meta", {})
        meta["symptom"] = session_ctx.symptom
    if session_ctx.hoop_size_mm:
        physical = report.setdefault("physical", {})
        if not physical.get("hoop_size_mm"):
            physical["hoop_size_mm"] = session_ctx.hoop_size_mm

    return report


def user_requests_preflight(user_message: str) -> bool:
    lowered = user_message.lower()
    triggers = (
        "preflight",
        "pre-flight",
        "pre check",
        "precheck",
        "run a check",
        "full review",
        "what's the verdict",
        "whats the verdict",
    )
    return any(trigger in lowered for trigger in triggers)


def has_design_uploaded(report: dict) -> bool:
    summary = report.get("summary") or {}
    count = summary.get("element_count")
    return isinstance(count, int) and count > 0


def user_describes_symptom(ctx: SessionContext) -> bool:
    return bool(ctx.symptom)
