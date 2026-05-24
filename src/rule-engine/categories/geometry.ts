import type { Rule } from "../types.js";
import { densityInteractionRiskFires } from "../categories/performance.js";
import { hasRunningDensityRisk } from "../utils/metrics.js";

export const geometryRules: Rule[] = [
  {
    id: "high_node_count",
    category: "geometry",
    severity: "medium",
    confidence: 0.75,
    fields: ["geometry.node_count"],
    title: "High node count",
    source:
      "docs/sources/community/reddit-troubleshoot-passes-no-stitch-out.md; docs/rules/issue-checker-cross-reference.md §8",
    suggested_action:
      "Simplify paths: Inkscape Path > Simplify (Ctrl+L)",
    check: (r) => r.geometry.node_count > 1000,
    detail: (r) =>
      `Node count is ${r.geometry.node_count} (threshold: 1000). High node counts cause slow rendering and export errors.`,
  },
  {
    id: "open_paths_present",
    category: "geometry",
    severity: "high",
    confidence: 0.9,
    fields: ["geometry.has_open_paths", "geometry.open_path_count"],
    title: "Open paths present",
    source: "docs/sources/inkstitch/troubleshoot.md; embroidery geometry best practice",
    suggested_action:
      "Close all open paths before export (Path > Object to Path, then check for open nodes)",
    skipWhen: (r) => r.geometry.has_open_paths === null,
    check: (r) => r.geometry.has_open_paths === true,
    detail: () =>
      "Design contains open paths. Open paths cause unpredictable stitch routing.",
  },
  {
    id: "high_overlap_ratio",
    category: "geometry",
    severity: "high",
    confidence: 0.8,
    fields: ["geometry.overlap_ratio"],
    title: "High overlap ratio",
    source: "docs/sources/community/failure-causes.md; density/overlap guidance",
    suggested_action:
      "Remove overlapping fills — use cutwork or proper layer ordering instead",
    skipWhen: (r) => r.geometry.overlap_ratio === null,
    check: (r) => r.geometry.overlap_ratio! > 0.3,
    detail: (r) =>
      `Overlap ratio is ${((r.geometry.overlap_ratio as number) * 100).toFixed(1)}% (threshold: 30%). Overlapping fills cause thread buildup and puckering.`,
  },
  {
    id: "design_exceeds_hoop",
    category: "geometry",
    severity: "critical",
    confidence: 0.95,
    fields: ["geometry.bounding_box", "physical.hoop_size_mm"],
    skipWhen: (r) =>
      r.physical.hoop_size_mm === null || r.geometry.bounding_box === null,
    title: "Design exceeds hoop",
    source: "production constraint / hoop boundaries",
    suggested_action:
      "Resize design to fit within hoop boundaries before export",
    check: (r) => {
      const bb = r.geometry.bounding_box!;
      const h = r.physical.hoop_size_mm!;
      return bb.w > h.w || bb.h > h.h;
    },
    detail: (r) => {
      const bb = r.geometry.bounding_box!;
      const h = r.physical.hoop_size_mm!;
      return `Design is ${bb.w}×${bb.h}mm, hoop is ${h.w}×${h.h}mm.`;
    },
  },
  {
    id: "too_many_paths",
    category: "geometry",
    severity: "low",
    confidence: 0.6,
    fields: ["geometry.path_count"],
    title: "Many paths",
    source: "conservative default; stitch file complexity",
    suggested_action:
      "Combine redundant paths to reduce stitch file complexity",
    check: (r) => r.geometry.path_count > 500,
    detail: (r) =>
      `Path count is ${r.geometry.path_count} (threshold: 500).`,
  },
  {
    id: "over_detailed_path",
    category: "geometry",
    group: "complexity",
    severity: "medium",
    confidence: 0.75,
    fields: ["geometry.avg_segment_length_mm"],
    title: "Over-detailed path",
    source: "rule-engine/heuristics: MCP avg segment length",
    suggested_action: "Simplify path to reduce unnecessary detail",
    check: (r) => {
      const avg = r.geometry.avg_segment_length_mm;
      return avg !== null && avg !== undefined && avg < 0.5;
    },
    detail: () =>
      "Very short segment lengths indicate overly detailed or fragmented path",
    evidence: (r) => ({
      avg_segment_length_mm: r.geometry.avg_segment_length_mm,
    }),
  },
  {
    id: "narrow_geometry_stitch_mismatch",
    category: "geometry",
    group: "feasibility",
    severity: "high",
    confidence: 0.85,
    fields: ["geometry.min_dimension_mm", "structure.stitch_types"],
    title: "Narrow geometry for stitch type",
    source:
      "rule-engine/heuristics: min dimension vs satin/fill stitch feasibility",
    suggested_action: "Use running stitch or increase shape width",
    check: (r) => {
      const minDim = r.geometry.min_dimension_mm;
      const stitchTypes = r.structure.stitch_types;
      const riskyStitch =
        stitchTypes.includes("satin") || stitchTypes.includes("fill");
      return (
        minDim !== null &&
        minDim !== undefined &&
        minDim < 1.0 &&
        riskyStitch
      );
    },
    detail: () =>
      "Geometry is too narrow for the selected stitch type (satin/fill)",
    evidence: (r) => ({
      min_dimension_mm: r.geometry.min_dimension_mm,
      stitch_types: r.structure.stitch_types,
    }),
  },
  {
    id: "running_stitch_density_risk",
    category: "geometry",
    group: "density",
    severity: "low",
    confidence: 0.7,
    fields: [
      "parameters.stitch_length_mm",
      "geometry.avg_segment_length_mm",
    ],
    title: "Running stitch density risk",
    source: "rule-engine/heuristics: short stitch length + high node count",
    suggested_action:
      "Increase stitch length slightly (1.8–2.0 mm) or simplify the path",
    skipWhen: (r) => r.parameters.stitch_length_mm === null,
    check: (r) =>
      hasRunningDensityRisk(r) && !densityInteractionRiskFires(r),
    detail: () =>
      "Short stitch length combined with many nodes may cause dense stitching and thread stress",
    evidence: (r) => ({
      stitch_length_mm: r.parameters.stitch_length_mm,
      avg_segment_length_mm: r.geometry.avg_segment_length_mm,
    }),
  },
];
