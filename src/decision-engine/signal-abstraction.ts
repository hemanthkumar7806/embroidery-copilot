import type { DesignReport, Issue } from "../rule-engine/types.js";

export type SignalInput = {
  report: DesignReport;
  issues: Issue[];
};

export type AbstractedCause = {
  id: string;
  cause: string;
  action: string;
  confidence: "low" | "medium" | "high";
};

export function abstractSignals(input: SignalInput): AbstractedCause | null {
  const { report, issues } = input;

  const minLen = report.geometry?.min_dimension_mm;
  const avgSeg = report.geometry?.avg_segment_length_mm;
  const nodeCount = report.geometry?.node_count || 0;

  const hasCross = issues.some((i) =>
    `${i.id} ${i.title ?? ""}`.toLowerCase().includes("cross"),
  );

  if (
    hasCross ||
    (minLen !== null && minLen === 0) ||
    (avgSeg !== null && avgSeg < 0.2)
  ) {
    return {
      id: "invalid_geometry_overlap",
      cause: "Invalid geometry — overlapping or zero-length nodes detected",
      action: "Use node tool and delete overlapping or duplicate nodes",
      confidence: "high",
    };
  }

  if (report.structure?.element_count === 0 && report.geometry?.node_count > 0) {
    return {
      id: "not_converted_to_path",
      cause: "Design is not converted into stitchable paths",
      action: "Convert all objects to path and ungroup everything",
      confidence: "high",
    };
  }

  if (avgSeg !== null && avgSeg < 0.5 && nodeCount > 100) {
    return {
      id: "over_detailed_path",
      cause: "Path is too detailed with too many small segments",
      action: "Simplify path to reduce node count",
      confidence: "medium",
    };
  }

  return null;
}
