"""Fabric presets: recommended embroidery parameters per fabric family.

The "correct" density / pull-compensation depends on the fabric — a light knit needs
different settings than denim. This mirrors the fabric-preset pattern used by commercial
tools (Wilcom's Auto Fabric Assistant) and the digitizing references (density ~0.3–0.6mm
by fabric). Values here are the STARTING points the auto-fix writes; the later LLM pass
can adapt from them.

Scope note: today only fix VALUES use these (row spacing, pull compensation). Detection
thresholds stay universal — see ROADMAP step 3. Underlay/stabilizer are stored for the
LLM pass (step 2) but not yet surfaced.
"""

from __future__ import annotations

from dataclasses import dataclass


# Below this row spacing a fill risks thread breakage / needle damage on ANY fabric.
DENSITY_HARD_MIN_MM = 0.25


@dataclass(frozen=True)
class FabricPreset:
    label: str
    row_spacing_mm: float        # nominal fill density (fix target); gap between rows
    row_spacing_min_mm: float    # densest acceptable spacing for this fabric (below = too dense)
    row_spacing_max_mm: float    # sparsest acceptable spacing (above = gaps show)
    pull_compensation_mm: float  # satin widening to counter pull on this fabric
    stitch_length_mm: float      # nominal running/fill stitch length
    underlay: str                # recommended underlay style (advice; used by LLM later)
    stabilizer: str              # recommended stabilizer (advice; used by LLM later)


# DEFAULT keeps the previously hardcoded behavior when the fabric is unknown: fix value
# 0.4mm, detection band 0.35–0.7mm (the old too_low/too_high thresholds).
DEFAULT = FabricPreset(
    label="general",
    row_spacing_mm=0.4,
    row_spacing_min_mm=0.35,
    row_spacing_max_mm=0.7,
    pull_compensation_mm=0.25,
    stitch_length_mm=2.5,
    underlay="edge_run",
    stabilizer="tear-away",
)

# Keyed by family. Bands seeded from digitizing references (see module docstring):
# nominal, density min, density max, pull-comp, stitch-len, underlay, stabilizer.
PRESETS: dict[str, FabricPreset] = {
    "cotton": FabricPreset("cotton", 0.45, 0.4, 0.5, 0.2, 2.5, "edge_run", "tear-away"),
    "knit": FabricPreset("knit / jersey", 0.45, 0.4, 0.5, 0.3, 2.5, "zigzag+edge_run", "cut-away"),
    "fleece": FabricPreset("fleece", 0.55, 0.5, 0.6, 0.25, 2.5, "zigzag", "cut-away"),
    "denim": FabricPreset("denim", 0.4, 0.3, 0.45, 0.15, 2.5, "edge_run", "tear-away"),
    "twill": FabricPreset("twill", 0.45, 0.4, 0.5, 0.2, 2.5, "zigzag", "tear-away"),
    "canvas": FabricPreset("canvas", 0.45, 0.4, 0.5, 0.2, 2.5, "zigzag", "tear-away"),
    "performance": FabricPreset(
        "performance polyester", 0.45, 0.4, 0.5, 0.2, 2.5, "edge_run", "cut-away"
    ),
    "leather": FabricPreset("leather", 0.5, 0.4, 0.6, 0.1, 2.5, "none", "tear-away"),
    "silk": FabricPreset("silk", 0.5, 0.4, 0.55, 0.15, 2.5, "center_run", "cut-away (light)"),
    "terry": FabricPreset("terry / towel", 0.5, 0.45, 0.6, 0.2, 2.5, "zigzag", "tear-away"),
}

# Normalized fabric strings (as produced by context_extractor / typed by users) -> family.
_ALIASES: dict[str, str] = {
    "cotton": "cotton",
    "knit": "knit",
    "jersey": "knit",
    "pique": "knit",
    "stretch": "knit",
    "lycra": "knit",
    "spandex": "knit",
    "fleece": "fleece",
    "sherpa": "fleece",
    "denim": "denim",
    "twill": "twill",
    "canvas": "canvas",
    "polyester": "performance",
    "poly": "performance",
    "performance": "performance",
    "leather": "leather",
    "silk": "silk",
    "terry": "terry",
    "towel": "terry",
}


def preset_for(fabric_type: str | None) -> FabricPreset:
    """Return the preset for a fabric string (family-normalized), or DEFAULT if unknown."""
    if not fabric_type or not isinstance(fabric_type, str):
        return DEFAULT
    key = fabric_type.strip().lower()
    family = _ALIASES.get(key)
    if family is None:
        # Substring fallback: "cotton polo" -> cotton, "poly blend" -> performance.
        for alias, fam in _ALIASES.items():
            if alias in key:
                family = fam
                break
    return PRESETS.get(family, DEFAULT) if family else DEFAULT


def fabric_families() -> list[dict[str, str]]:
    """Pickable families for the UI: [{value, label}], stable order."""
    return [{"value": key, "label": preset.label} for key, preset in PRESETS.items()]
