import type { Rule } from "../types.js";

export const structureRules: Rule[] = [
  {
    id: "missing_underlay",
    category: "structure",
    severity: "high",
    confidence: 0.8,
    fields: ["structure.has_underlay", "structure.stitch_types"],
    title: "Fill without underlay",
    source: "docs/sources/inkstitch/tutorial-underlay.md",
    suggested_action:
      "Add underlay stitches in Ink/Stitch — use edge-walk for light fabrics, grid for heavy",
    check: (r) =>
      !r.structure.has_underlay && r.structure.stitch_types.includes("fill"),
    detail: () =>
      "Fill stitches found but no underlay detected. Fills without underlay shift and distort on most fabrics.",
  },
  {
    id: "hidden_layers_present",
    category: "structure",
    severity: "medium",
    confidence: 0.9,
    fields: ["structure.has_hidden_layers"],
    title: "Hidden layers present",
    source: "Inkscape / export hygiene",
    suggested_action:
      "Delete or show all hidden layers and review before export",
    check: (r) => r.structure.has_hidden_layers === true,
    detail: () =>
      "Hidden layers detected. Hidden layers may export unexpectedly and add unwanted stitches.",
  },
  {
    id: "no_stitch_types_detected",
    category: "structure",
    severity: "critical",
    confidence: 0.95,
    fields: ["structure.stitch_types"],
    title: "No stitch types detected",
    source: "docs/sources/inkstitch/params-overview.md",
    suggested_action:
      "Select paths and apply Ink/Stitch params via Extensions > Ink/Stitch > Params",
    check: (r) => r.structure.stitch_types.length === 0,
    detail: () =>
      "No embroidery stitch objects found. Design objects must have Ink/Stitch params applied.",
  },
  {
    id: "excessive_element_count",
    category: "structure",
    severity: "medium",
    confidence: 0.65,
    fields: ["structure.element_count"],
    title: "High element count",
    source: "docs/rules/issue-checker-cross-reference.md §8 (performance)",
    suggested_action:
      "Merge or simplify elements where possible before simulation",
    check: (r) => r.structure.element_count > 200,
    detail: (r) =>
      `Element count is ${r.structure.element_count} (threshold: 200). Large element counts significantly increase simulation and export time.`,
  },
  {
    id: "satin_without_underlay",
    category: "structure",
    severity: "high",
    confidence: 0.82,
    fields: ["structure.stitch_types", "structure.has_underlay"],
    title: "Satin without underlay",
    source: "docs/sources/inkstitch/stitch-satin.md",
    suggested_action:
      "Add zigzag or edge-walk underlay to all satin columns",
    check: (r) =>
      r.structure.stitch_types.includes("satin") && !r.structure.has_underlay,
    detail: () =>
      "Satin columns found without underlay. Satin without underlay sinks into fabric and loses definition.",
  },
  {
    id: "mixed_stitch_no_routing",
    category: "structure",
    severity: "medium",
    confidence: 0.6,
    fields: ["structure.stitch_types", "routing.jump_stitch_count"],
    skipWhen: (r) => r.routing.jump_stitch_count === null,
    title: "Mixed stitch types with many jumps",
    source: "docs/sources/inkstitch/tutorial-routing.md",
    suggested_action:
      "Re-sequence stitch order to group same-type elements and reduce jumps",
    check: (r) =>
      r.structure.stitch_types.length > 2 &&
      r.routing.jump_stitch_count! > 20,
    detail: (r) =>
      `${r.structure.stitch_types.length} stitch types with ${r.routing.jump_stitch_count} jump stitches. Poor routing between stitch types causes unnecessary jumps.`,
  },
];
