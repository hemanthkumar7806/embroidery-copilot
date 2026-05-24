import type { DesignReport, Issue } from "../rule-engine/types.js";

export type FailureType =
  | "geometry"
  | "structure"
  | "parameter"
  | "routing"
  | "unknown";

export type ClassificationResult = {
  type: FailureType;
  confidence: "low" | "medium" | "high";
  reason: string;
};

export function classifyFailure(
  report: DesignReport,
  _issues: Issue[],
): ClassificationResult {
  const elementCount = report.structure?.element_count;
  const nodeCount = report.geometry?.node_count;
  const hasGeometry = nodeCount !== null && nodeCount !== undefined && nodeCount > 0;

  if (elementCount === 0 && hasGeometry) {
    return {
      type: "structure",
      confidence: "high",
      reason: "Geometry exists but no stitch elements detected",
    };
  }

  const summaryWithHiddenCount = report.summary as { hidden_layer_count?: number } | undefined;
  const hiddenLayerCount = summaryWithHiddenCount?.hidden_layer_count ?? 0;

  if (report.structure?.has_hidden_layers || hiddenLayerCount > 0) {
    return {
      type: "structure",
      confidence: "medium",
      reason: "Hidden layers detected",
    };
  }

  const stitchTypes = report.structure?.stitch_types || [];

  if (
    stitchTypes.includes("running") &&
    stitchTypes.includes("satin") &&
    (report.structure?.element_count ?? 0) > 20
  ) {
    return {
      type: "parameter",
      confidence: "medium",
      reason: "Mixed stitch types suggest param inconsistency",
    };
  }

  if (report.export?.format === null) {
    return {
      type: "parameter",
      confidence: "low",
      reason: "Missing export format",
    };
  }

  const minDim = report.geometry?.min_dimension_mm;
  const avgSeg = report.geometry?.avg_segment_length_mm;

  if (minDim !== null && minDim !== undefined && minDim < 1.0) {
    return {
      type: "geometry",
      confidence: "high",
      reason: "Very narrow geometry detected",
    };
  }

  if (avgSeg !== null && avgSeg !== undefined && avgSeg < 0.5) {
    return {
      type: "geometry",
      confidence: "medium",
      reason: "Highly fragmented path",
    };
  }

  if (report.routing?.jump_stitch_count === null) {
    return {
      type: "routing",
      confidence: "low",
      reason: "Routing data missing",
    };
  }

  return {
    type: "unknown",
    confidence: "low",
    reason: "No strong signal detected",
  };
}
