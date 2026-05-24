import type {
  DesignReport,
  DryRunEvaluation,
  GapReport,
  Issue,
  Rule,
} from "./types.js";

export const CANONICAL_LEAF_PATHS: string[] = [
  "geometry.node_count",
  "geometry.path_count",
  "geometry.bounding_box",
  "geometry.has_open_paths",
  "geometry.open_path_count",
  "geometry.overlap_ratio",
  "geometry.path_length_mm",
  "geometry.avg_segment_length_mm",
  "geometry.min_dimension_mm",
  "summary.total_path_length_mm",
  "summary.avg_segment_length_global",
  "parameters.row_spacing_mm",
  "parameters.stitch_length_mm",
  "parameters.pull_compensation_mm",
  "parameters.density_value",
  "structure.layer_count",
  "structure.has_hidden_layers",
  "structure.has_underlay",
  "structure.stitch_types",
  "structure.element_count",
  "routing.jump_stitch_count",
  "routing.trim_count",
  "routing.color_change_count",
  "routing.estimated_stitch_count",
  "routing.has_short_runs",
  "export.format",
  "export.software_version",
  "export.has_metadata",
  "physical.fabric_type",
  "physical.hoop_size_mm",
  "physical.machine_type",
];

export function analyzeGaps(
  report: DesignReport,
  result: { issues: Issue[]; dryRunEvaluations?: DryRunEvaluation[] },
  allRules: Rule[],
): GapReport {
  const allReadFields = new Set(allRules.flatMap((r) => r.fields));
  const unchecked_fields = CANONICAL_LEAF_PATHS.filter(
    (p) => !allReadFields.has(p),
  );

  const low_confidence_rules = allRules
    .filter((r) => r.confidence < 0.6)
    .map((r) => r.id);

  const physicalNullFields: string[] = [];
  if (report.physical.fabric_type === null)
    physicalNullFields.push("fabric_type");
  if (report.physical.hoop_size_mm === null)
    physicalNullFields.push("hoop_size_mm");
  if (report.physical.machine_type === null)
    physicalNullFields.push("machine_type");

  const skipped_rules = (result.dryRunEvaluations ?? [])
    .filter((e) => e.skipped)
    .map((e) => e.rule_id);

  const soft_rules = result.issues
    .filter((i) => i.confidence < 0.7)
    .map((i) => i.id);

  return {
    unchecked_fields,
    low_confidence_rules,
    missing_physical_data: physicalNullFields,
    soft_rules,
    skipped_rules,
  };
}

/** For tests: verify every canonical path resolves on a full sample report */
export function flattenReportPaths(obj: unknown, prefix = ""): Set<string> {
  const keys = new Set<string>();
  if (obj === null || typeof obj !== "object") {
    if (prefix) keys.add(prefix);
    return keys;
  }
  if (Array.isArray(obj)) {
    if (prefix) keys.add(prefix);
    return keys;
  }
  for (const [k, v] of Object.entries(obj)) {
    const p = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      for (const sub of flattenReportPaths(v, p)) keys.add(sub);
    } else {
      keys.add(p);
    }
  }
  return keys;
}
