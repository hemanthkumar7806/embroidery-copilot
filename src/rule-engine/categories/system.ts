import type { DesignReport, Rule } from "../types.js";

function getHiddenLayerCount(report: DesignReport): number | null {
  const value = (report.summary as Record<string, unknown>)["hidden_layer_count"];
  return typeof value === "number" ? value : null;
}

const hiddenLayerStitchRisk: Rule = {
  id: "hidden_layer_stitch_risk",
  category: "structure",
  group: "root_cause",
  severity: "high",
  confidence: 0.9,
  fields: ["summary.hidden_layer_count"],
  skipWhen: (report) => getHiddenLayerCount(report) === null,
  title: "Hidden layer stitch risk",
  source: "root cause system checks",
  suggested_action: "Remove hidden layers or unhide and validate before export",
  check: (report) => {
    const hidden = getHiddenLayerCount(report);
    return hidden !== null && hidden > 0;
  },
  detail: () => "Hidden layers may still be stitched by the machine",
  evidence: (report) => ({
    hidden_layer_count: getHiddenLayerCount(report),
  }),
};

const stitchTypeLossRisk: Rule = {
  id: "stitch_type_loss_risk",
  category: "structure",
  group: "root_cause",
  severity: "high",
  confidence: 0.85,
  fields: ["structure.stitch_types", "structure.element_count"],
  skipWhen: (report) => report.structure.element_count === null,
  title: "Stitch type loss risk",
  source: "root cause system checks",
  suggested_action: "Reapply stitch params and avoid lossy conversion steps",
  check: (report) => {
    const types = report.structure.stitch_types || [];
    const count = report.structure.element_count;
    return (
      types.includes("running") &&
      types.includes("satin") &&
      count !== null &&
      count > 20
    );
  },
  detail: () =>
    "Unexpected mix of stitch types may indicate parameter loss or incorrect conversion",
  evidence: (report) => ({
    stitch_types: report.structure.stitch_types,
    element_count: report.structure.element_count,
  }),
};

const exportParamMismatchRisk: Rule = {
  id: "export_param_mismatch_risk",
  category: "export",
  group: "root_cause",
  severity: "medium",
  confidence: 0.8,
  fields: ["export.format", "export.software_version"],
  title: "Export parameter mismatch risk",
  source: "root cause system checks",
  suggested_action: "Export with complete metadata and verify software compatibility",
  check: (report) => {
    const format = report.export.format;
    const version = report.export.software_version;
    return format === null || version === null;
  },
  detail: () =>
    "Export metadata is incomplete; machine may interpret design incorrectly",
  evidence: (report) => ({
    format: report.export.format,
    software_version: report.export.software_version,
  }),
};

const fabricInstabilityRisk: Rule = {
  id: "fabric_instability_risk",
  category: "physical",
  group: "root_cause",
  severity: "medium",
  confidence: 0.75,
  fields: ["physical.fabric_type"],
  title: "Fabric instability risk",
  source: "root cause system checks",
  suggested_action: "Set fabric type and adjust stabilizer before stitching",
  check: (report) => report.physical.fabric_type === null,
  detail: () =>
    "Fabric type not specified; stretch fabrics may distort stitching",
  evidence: (report) => ({
    fabric_type: report.physical.fabric_type,
  }),
};

const trimBehaviorRisk: Rule = {
  id: "trim_behavior_risk",
  category: "routing",
  group: "root_cause",
  severity: "medium",
  confidence: 0.75,
  fields: ["routing.jump_stitch_count"],
  title: "Trim behavior risk",
  source: "root cause system checks",
  suggested_action: "Verify trim settings and run machine preview on target format",
  check: (report) => report.routing.jump_stitch_count === null,
  detail: () =>
    "Trim/jump behavior unknown; machine may leave threads between elements",
  evidence: (report) => ({
    jump_stitch_count: report.routing.jump_stitch_count,
  }),
};

export const systemRules: Rule[] = [
  hiddenLayerStitchRisk,
  stitchTypeLossRisk,
  exportParamMismatchRisk,
  fabricInstabilityRisk,
  trimBehaviorRisk,
];
