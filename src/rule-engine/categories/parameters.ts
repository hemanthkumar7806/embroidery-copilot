import type { Rule } from "../types.js";

export const parameterRules: Rule[] = [
  {
    id: "row_spacing_too_low",
    category: "parameters",
    severity: "high",
    confidence: 0.85,
    fields: ["parameters.row_spacing_mm"],
    skipWhen: (r) => r.parameters.row_spacing_mm === null,
    title: "Row spacing too low",
    source: "docs/sources/inkstitch/stitch-fill.md; extracted-data.md",
    suggested_action:
      "Increase row spacing to minimum 0.35mm in Ink/Stitch fill settings",
    check: (r) => r.parameters.row_spacing_mm! < 0.35,
    detail: (r) =>
      `Row spacing is ${r.parameters.row_spacing_mm}mm (minimum: 0.35mm). Dense fills cause thread breakage and fabric damage.`,
  },
  {
    id: "row_spacing_too_high",
    category: "parameters",
    severity: "medium",
    confidence: 0.7,
    fields: ["parameters.row_spacing_mm"],
    skipWhen: (r) => r.parameters.row_spacing_mm === null,
    title: "Row spacing too high",
    source: "docs/sources/inkstitch/stitch-fill.md",
    suggested_action:
      "Decrease row spacing — gaps between rows will show in finished embroidery",
    check: (r) => r.parameters.row_spacing_mm! > 0.55,
    detail: (r) =>
      `Row spacing is ${r.parameters.row_spacing_mm}mm (maximum recommended: 0.55mm). Gaps will be visible in stitch-out.`,
  },
  {
    id: "stitch_length_too_short",
    category: "parameters",
    severity: "high",
    confidence: 0.85,
    fields: ["parameters.stitch_length_mm"],
    skipWhen: (r) => r.parameters.stitch_length_mm === null,
    title: "Stitch length too short",
    source: "docs/sources/inkstitch/extracted-data.md; running stitch params",
    suggested_action: "Set minimum stitch length to 1.5mm in Ink/Stitch params",
    check: (r) => r.parameters.stitch_length_mm! < 1.5,
    detail: (r) =>
      `Stitch length is ${r.parameters.stitch_length_mm}mm (minimum: 1.5mm). Very short stitches shred thread and damage fabric.`,
  },
  {
    id: "stitch_length_too_long",
    category: "parameters",
    severity: "medium",
    confidence: 0.75,
    fields: ["parameters.stitch_length_mm"],
    skipWhen: (r) => r.parameters.stitch_length_mm === null,
    title: "Stitch length too long",
    source: "docs/sources/inkstitch/extracted-data.md",
    suggested_action:
      "Keep stitches under 6mm — add intermediate stitches for long spans",
    check: (r) => r.parameters.stitch_length_mm! > 6.0,
    detail: (r) =>
      `Stitch length is ${r.parameters.stitch_length_mm}mm (maximum: 6.0mm). Long stitches snag and distort easily.`,
  },
  {
    id: "pull_compensation_missing",
    category: "parameters",
    severity: "medium",
    confidence: 0.65,
    fields: ["parameters.pull_compensation_mm", "structure.stitch_types"],
    skipWhen: (r) =>
      r.parameters.pull_compensation_mm === null ||
      !r.structure.stitch_types.includes("fill"),
    title: "Pull compensation missing on fill",
    source: "docs/sources/inkstitch/tutorial-pull-compensation.md",
    suggested_action:
      "Add pull compensation 0.2–0.3mm for woven fabric, higher for stretch fabrics",
    check: (r) =>
      r.parameters.pull_compensation_mm === 0 &&
      r.structure.stitch_types.includes("fill"),
    detail: () =>
      "Pull compensation is 0mm on a design with fill stitches. Fill stitches pull fabric inward — compensation prevents size distortion.",
  },
  {
    id: "extreme_density",
    category: "parameters",
    severity: "high",
    confidence: 0.8,
    fields: ["parameters.density_value"],
    skipWhen: (r) => r.parameters.density_value === null,
    title: "Extreme density",
    source: "docs/sources/inkstitch/stitch-fill.md; community failure-causes.md",
    suggested_action:
      "Reduce density — if design requires detail, consider splitting into multiple passes",
    check: (r) => r.parameters.density_value! > 0.6,
    detail: (r) =>
      `Density value is ${r.parameters.density_value} (threshold: 0.6). Extreme density causes needle breakage and fabric damage.`,
  },
];
