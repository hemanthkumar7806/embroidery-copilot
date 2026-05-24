/**
 * One-shot: bridge-shaped JSON → normalizeDesignReport → runRuleEngine (+ dryRun).
 * Paste MCP `get_design_report` output as BRIDGE_JSON env or default to bridge-live-capture.json.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  normalizeDesignReport,
  runRuleEngine,
  ALL_RULES,
} from "../src/rule-engine/index.js";
import { buildDecision } from "../src/decision-engine/index.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const liveCapture = JSON.parse(
  readFileSync(join(__dirname, "bridge-live-capture.json"), "utf8"),
) as {
  elements: unknown[];
  summary: Record<string, unknown>;
  parse_warnings?: unknown[];
};

const docInfo = {
  path: String(liveCapture.summary.document_path),
  name: String(liveCapture.summary.document_name),
  width: "210mm",
  height: "297mm",
  viewBox: String(liveCapture.summary.viewBox),
};

const defaultBridge = {
  elements: liveCapture.elements,
  summary: liveCapture.summary,
};

const bridge =
  process.env.BRIDGE_JSON !== undefined
    ? JSON.parse(process.env.BRIDGE_JSON)
    : defaultBridge;

const designReportPayload = {
  document_info: docInfo,
  design_report: {
    elements: liveCapture.elements,
    parse_warnings: liveCapture.parse_warnings ?? [],
    summary: liveCapture.summary,
  },
  note:
    "get_design_context() is not an MCP tool here; equivalent = get_document_info + get_design_report(include_geometry:true).",
};

console.log(
  JSON.stringify(
    { step: "STEP_1_combined_context_like_object", design_context: designReportPayload },
    null,
    2,
  ),
);

const report = normalizeDesignReport(bridge);
console.log(
  JSON.stringify({ step: "STEP_2_normalized_report", report }, null, 2),
);

const engine = runRuleEngine(report);
const { issues, summary, gaps, decision } = engine;
const guided_decision = buildDecision({ issues, report });
console.log(
  JSON.stringify(
    {
      step: "STEP_3_rule_engine",
      issues,
      summary,
      gaps,
      decision,
      guided_decision,
    },
    null,
    2,
  ),
);

const dry = runRuleEngine(report, { dryRun: true });
const dryList =
  dry.dryRunEvaluations?.map((e) => ({
    rule_id: e.rule_id,
    fired: e.fired,
    confidence: e.confidence,
  })) ?? [];
console.log(JSON.stringify({ step: "STEP_4_dry_run", dry_run: dryList }, null, 2));

const watch = [
  "stitch_count_risk",
  "over_detailed_path",
  "narrow_geometry_stitch_mismatch",
  "global_complexity_risk",
] as const;
const firedIds = new Set(issues.map((i) => i.id));
const pl = report.geometry.path_length_mm;
const st = report.parameters.stitch_length_mm;
const est =
  pl != null && st != null && st !== 0 ? pl / st : null;
const step5 = {
  stitch_count_risk: {
    fired: firedIds.has("stitch_count_risk"),
    path_length_mm: pl,
    stitch_length_mm: st,
    estimated_stitches: est,
    why:
      pl == null || st == null || !pl || !st
        ? "length or stitch null/0 → check returns false (skip)"
        : est! > 3000
          ? `estimated ${est!.toFixed(1)} > 3000`
          : `estimated ${est!.toFixed(1)} ≤ 3000`,
  },
  over_detailed_path: {
    fired: firedIds.has("over_detailed_path"),
    avg_segment_length_mm: report.geometry.avg_segment_length_mm,
    why:
      report.geometry.avg_segment_length_mm == null
        ? "avg_segment_length_mm null → false"
        : report.geometry.avg_segment_length_mm! < 0.5
          ? `avg ${report.geometry.avg_segment_length_mm} < 0.5`
          : `avg ${report.geometry.avg_segment_length_mm} ≥ 0.5`,
  },
  narrow_geometry_stitch_mismatch: {
    fired: firedIds.has("narrow_geometry_stitch_mismatch"),
    min_dimension_mm: report.geometry.min_dimension_mm,
    risky_stitch_satin_or_fill:
      report.structure.stitch_types.includes("satin") ||
      report.structure.stitch_types.includes("fill"),
    why: (() => {
      const minDim = report.geometry.min_dimension_mm;
      const risky =
        report.structure.stitch_types.includes("satin") ||
        report.structure.stitch_types.includes("fill");
      if (minDim == null)
        return "min_dimension_mm null → false";
      if (!risky) return "no satin/fill in stitch_types → false";
      return minDim < 1.0
        ? `min ${minDim} < 1.0 and satin/fill`
        : `min ${minDim} ≥ 1.0`;
    })(),
  },
  global_complexity_risk: {
    fired: firedIds.has("global_complexity_risk"),
    total_path_length_mm: report.summary.total_path_length_mm,
    avg_segment_length_global: report.summary.avg_segment_length_global,
    why:
      report.summary.total_path_length_mm == null ||
      report.summary.avg_segment_length_global == null
        ? "summary fields null → false"
        : report.summary.total_path_length_mm! > 2000 &&
            report.summary.avg_segment_length_global! < 1.0
          ? "total>2000 and avg<1.0"
          : "thresholds not met (need both: total>2000 and global avg<1.0)",
  },
};
console.log(JSON.stringify({ step: "STEP_5_new_rules", rules: step5 }, null, 2));

const issueFieldMap: Record<string, string> = {
  stitch_count_risk: "geometry.path_length_mm + parameters.stitch_length_mm",
  over_detailed_path: "geometry.avg_segment_length_mm",
  narrow_geometry_stitch_mismatch:
    "geometry.min_dimension_mm + structure.stitch_types",
  global_complexity_risk:
    "summary.total_path_length_mm + summary.avg_segment_length_global",
};
const step6 = issues.map((i) => ({
  id: i.id,
  mcp_or_report_field: issueFieldMap[i.id] ?? "(see rule.fields)",
  evidence: i.evidence ?? null,
  detail: i.detail,
}));
console.log(JSON.stringify({ step: "STEP_6_data_usage", issues: step6 }, null, 2));
