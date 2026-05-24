import type { DesignReport, Issue } from "../rule-engine/types.js";
import type { RootCause } from "./root-cause.js";

export type CauseMapping = {
  id: string;
  match: (report: DesignReport, issues: Issue[]) => boolean;
} & RootCause;

export const CAUSE_MAPPINGS: CauseMapping[] = [
  {
    id: "svg_structure_invalid",
    match: (report) => {
      const nodeCount = report.geometry?.node_count;
      return report.structure?.element_count === 0 && nodeCount !== null && nodeCount > 0;
    },
    cause: "SVG uses non-path elements (clones/groups) not recognized by Ink/Stitch",
    action: "Convert all objects to path and ungroup everything",
    confidence: "certain",
  },
  {
    id: "duplicate_nodes_overlap",
    match: (report, issues) => {
      // 🔥 Detect cross/intersection errors
      const hasCrossError = issues.some((i) => {
        const text = `${i.id} ${i.title ?? ""} ${i.detail ?? ""}`.toLowerCase();
        return (
          text.includes("cross") ||
          text.includes("intersection") ||
          text.includes("overlap")
        );
      });

      // 🔥 Detect strong symptom signal
      const symptom = report.meta?.symptom?.toLowerCase?.() || "";
      const hasMoveSymptom =
        symptom.includes("disappear") ||
        symptom.includes("move") ||
        symptom.includes("slight");

      return hasCrossError || hasMoveSymptom;
    },
    cause: "Two nodes are overlapping at the same position",
    action: "Use node tool, zoom in, and delete the overlapping node",
    confidence: "high",
  },
  {
    id: "hidden_duplicate_layers",
    match: (report) => {
      const hiddenLayerCount = report.summary?.hidden_layer_count;
      return hiddenLayerCount !== null && hiddenLayerCount !== undefined && hiddenLayerCount > 0;
    },
    cause: "Hidden layers contain duplicate stitch objects",
    action: "Remove hidden layers before export",
    confidence: "high",
  },
  {
    id: "narrow_satin_issue",
    match: (report) => {
      const minDim = report.geometry?.min_dimension_mm;
      const types = report.structure?.stitch_types || [];

      return minDim !== null && minDim !== undefined && minDim < 1.0 && types.includes("satin");
    },
    cause: "Satin stitch used on geometry too narrow",
    action: "Convert narrow areas to running stitch or widen shape",
    confidence: "high",
  },
  {
    id: "density_overload",
    match: (report) => {
      const stitchLen = report.parameters?.stitch_length_mm;
      const nodes = report.geometry?.node_count;
      return (
        stitchLen !== null &&
        stitchLen !== undefined &&
        nodes !== null &&
        nodes !== undefined &&
        stitchLen <= 1.5 &&
        nodes > 500
      );
    },
    cause: "Too many stitches concentrated in small area",
    action: "Increase stitch length or simplify geometry",
    confidence: "high",
  },
  {
    id: "precision_tolerance_issue",
    match: (report) => {
      const avgSeg = report.geometry?.avg_segment_length_mm;
      return avgSeg !== null && avgSeg !== undefined && avgSeg < 0.3;
    },
    cause: "Geometry is too fine and triggers precision tolerance limits",
    action: "Lightly simplify path or round node positions",
    confidence: "medium",
  },
  {
    id: "over_detailed_path",
    match: (report) => {
      const avgSeg = report.geometry?.avg_segment_length_mm;
      return avgSeg !== null && avgSeg !== undefined && avgSeg < 0.5;
    },
    cause: "Path has too many tiny segments",
    action: "Simplify path to reduce node count",
    confidence: "medium",
  },
  {
    id: "trim_missing",
    match: (report) => report.routing?.jump_stitch_count === null,
    cause: "Trim behavior not defined in design",
    action: "Enable trim settings in Ink/Stitch before export",
    confidence: "medium",
  },
  {
    id: "stitch_type_mismatch",
    match: (report) => {
      const types = report.structure?.stitch_types || [];
      return types.includes("running") && types.includes("satin");
    },
    cause: "Mixed stitch types may indicate param loss",
    action: "Reapply correct stitch type settings",
    confidence: "medium",
  },
  {
    id: "fabric_instability",
    match: (report) => report.physical?.fabric_type === null,
    cause: "Fabric type unknown or unstable",
    action: "Use cutaway stabilizer and proper hooping",
    confidence: "low",
  },
];

export function resolveRootCause(
  report: DesignReport,
  issues: Issue[],
): CauseMapping | null {
  console.log("ISSUE IDS:", issues.map((i) => i.id));
  console.log("SYMPTOM:", report.meta?.symptom);
  for (const mapping of CAUSE_MAPPINGS) {
    const matched = mapping.match(report, issues);

    if (matched) {
      console.log("✅ MATCHED ROOT CAUSE:", mapping.id, mapping.confidence);
      return mapping;
    }
  }
  return null;
}
