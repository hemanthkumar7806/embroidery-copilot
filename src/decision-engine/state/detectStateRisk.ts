import type { NormalizedDesignReport } from "../normalize/normalizeDesignReport.js";

export type StateRisk = {
  type: "STATE_DESYNC" | "COMPOUND_PATH_CONFUSION" | "CORRUPTED_PATH_STATE";
  element: string;
  confidence: number;
};

export function detectStateRisk(report: NormalizedDesignReport): StateRisk[] {
  const risks: StateRisk[] = [];

  for (const el of report.elements) {
    const hasInkstitch = el.hasInkstitchAttrs;

    if (hasInkstitch && el.stitch_type === "stroke") {
      risks.push({
        type: "STATE_DESYNC",
        element: el.id,
        confidence: 0.85,
      });
    }

    if (el.subpath_count > 1 && el.isSingleStrokeVisual) {
      risks.push({
        type: "COMPOUND_PATH_CONFUSION",
        element: el.id,
        confidence: 0.7,
      });
    }

    if (el.min_segment_length === 0 && hasInkstitch) {
      risks.push({
        type: "CORRUPTED_PATH_STATE",
        element: el.id,
        confidence: 0.75,
      });
    }
  }

  return risks;
}
