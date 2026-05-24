import type { DesignReport, Rule } from "../types.js";
import { computeComplexityScore, isFragmented } from "../utils/metrics.js";

export function densityInteractionRiskFires(report: DesignReport): boolean {
  return (
    report.parameters.stitch_length_mm !== null &&
    report.parameters.stitch_length_mm <= 1.5 &&
    report.geometry.node_count > 120 &&
    report.structure.element_count > 1
  );
}

function insufficientDataNullCount(report: {
  parameters: { row_spacing_mm: number | null };
  routing: { estimated_stitch_count: number | null };
  physical: { fabric_type: string | null };
  geometry: { bounding_box: { w: number; h: number } | null };
}): { count: number; nullFields: string[] } {
  const fields: [string, unknown][] = [
    ["parameters.row_spacing_mm", report.parameters.row_spacing_mm],
    ["routing.estimated_stitch_count", report.routing.estimated_stitch_count],
    ["physical.fabric_type", report.physical.fabric_type],
    ["geometry.bounding_box", report.geometry.bounding_box],
  ];
  const nullFields = fields.filter(([, v]) => v === null).map(([k]) => k);
  return { count: nullFields.length, nullFields };
}

export const performanceRules: Rule[] = [
  {
    id: "simulation_freeze_risk",
    category: "performance",
    group: "performance",
    severity: "critical",
    confidence: 0.85,
    fields: [
      "geometry.node_count",
      "geometry.path_count",
      "structure.element_count",
    ],
    title: "Simulation freeze risk",
    source: "rule-engine/heuristics: complexity vs path fragmentation",
    suggested_action:
      "Simplify paths, reduce node count, and avoid excessive fragmentation",
    check: (r) =>
      computeComplexityScore(r) > 0.8 ||
      (r.geometry.node_count > 800 && r.geometry.path_count > 200),
    detail: (r) => {
      const score = computeComplexityScore(r);
      return `High simulator load risk: node_count=${r.geometry.node_count}, path_count=${r.geometry.path_count}, complexity_score=${score.toFixed(3)}.`;
    },
    evidence: (r) => ({
      node_count: r.geometry.node_count,
      path_count: r.geometry.path_count,
      element_count: r.structure.element_count,
      complexity_score: computeComplexityScore(r),
    }),
  },
  {
    id: "high_complexity_design",
    category: "performance",
    group: "performance",
    severity: "high",
    confidence: 0.8,
    fields: [
      "geometry.node_count",
      "geometry.path_count",
      "structure.element_count",
    ],
    title: "High design complexity",
    source: "rule-engine/heuristics: weighted complexity score",
    suggested_action:
      "Simplify paths or reduce element count before simulation",
    check: (r) => computeComplexityScore(r) > 0.6,
    detail: (r) => {
      const score = computeComplexityScore(r);
      return `Design complexity score is ${score.toFixed(3)}, which may slow simulation`;
    },
  },
  {
    id: "excessive_fragmentation",
    category: "performance",
    group: "performance",
    severity: "medium",
    confidence: 0.75,
    fields: ["structure.element_count", "geometry.path_count"],
    title: "Excessive fragmentation",
    source: "rule-engine/heuristics: many elements and paths",
    suggested_action: "Merge paths or reduce object count where possible",
    check: (r) => isFragmented(r),
    detail: () =>
      "Design contains many small elements and paths, increasing computation cost",
  },
  {
    id: "density_interaction_risk",
    category: "performance",
    group: "interaction",
    severity: "high",
    confidence: 0.8,
    fields: [
      "parameters.stitch_length_mm",
      "geometry.node_count",
      "structure.element_count",
    ],
    title: "Density interaction risk",
    source: "rule-engine/heuristics: stitch length × node density × elements",
    suggested_action: "Increase stitch length OR reduce path complexity",
    check: (r) => densityInteractionRiskFires(r),
    detail: () =>
      "Combination of short stitch length and high node count increases needle penetration density significantly",
    evidence: (r) => ({
      stitch_length_mm: r.parameters.stitch_length_mm,
      node_count: r.geometry.node_count,
      element_count: r.structure.element_count,
    }),
  },
  {
    id: "insufficient_data_risk",
    category: "performance",
    group: "gaps",
    severity: "low",
    confidence: 0.6,
    fields: [
      "parameters.row_spacing_mm",
      "routing.estimated_stitch_count",
      "physical.fabric_type",
      "geometry.bounding_box",
    ],
    title: "Insufficient data for full analysis",
    source: "rule-engine/gaps: key report fields null",
    suggested_action: "Provide missing measurements in the design pipeline",
    check: (r) => insufficientDataNullCount(r).count > 2,
    detail: (r) => {
      const { count, nullFields } = insufficientDataNullCount(r);
      return `Several critical fields are missing (${count} null), limiting accurate analysis: ${nullFields.join(", ")}`;
    },
    evidence: (r) => {
      const { count, nullFields } = insufficientDataNullCount(r);
      return { null_field_count: count, null_fields: nullFields };
    },
  },
  {
    id: "stitch_count_risk",
    category: "performance",
    group: "stitch_density",
    severity: "medium",
    confidence: 0.8,
    fields: ["geometry.path_length_mm", "parameters.stitch_length_mm"],
    title: "High estimated stitch count",
    source: "rule-engine/heuristics: path length / stitch length",
    suggested_action: "Increase stitch length or simplify the path",
    check: (r) => {
      const length = r.geometry.path_length_mm;
      const stitch = r.parameters.stitch_length_mm;
      if (length && stitch) {
        const estimated = length / stitch;
        return estimated > 3000;
      }
      return false;
    },
    detail: () =>
      "Estimated stitch count is high based on path length and stitch length",
  },
  {
    id: "global_complexity_risk",
    category: "performance",
    group: "complexity",
    severity: "medium",
    confidence: 0.7,
    fields: [
      "summary.total_path_length_mm",
      "summary.avg_segment_length_global",
    ],
    title: "Global design complexity",
    source: "rule-engine/heuristics: document path length and segment length",
    suggested_action:
      "Simplify paths or reduce fragmentation to improve simulation performance",
    check: (r) => {
      const total = r.summary.total_path_length_mm;
      const avg = r.summary.avg_segment_length_global;
      return (
        total !== null &&
        total !== undefined &&
        avg !== null &&
        avg !== undefined &&
        total > 2000 &&
        avg < 1.0
      );
    },
    detail: () =>
      "Overall design complexity may impact simulation or stitching performance",
  },
];
