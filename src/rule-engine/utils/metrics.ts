import type { DesignReport } from "../types.js";

export function computeComplexityScore(report: DesignReport): number {
  const nodeFactor = report.geometry.node_count / 1000;
  const pathFactor = report.geometry.path_count / 200;
  const elementFactor = report.structure.element_count / 100;

  return nodeFactor * 0.5 + pathFactor * 0.3 + elementFactor * 0.2;
}

export function isFragmented(report: DesignReport): boolean {
  return report.structure.element_count > 100 && report.geometry.path_count > 200;
}

export function hasRunningDensityRisk(report: DesignReport): boolean {
  const stitch = report.parameters.stitch_length_mm;
  if (stitch === null || stitch > 1.5) return false;

  const avgSeg = report.geometry.avg_segment_length_mm;
  if (avgSeg === null || avgSeg === undefined) {
    return report.geometry.node_count > 80;
  }
  return report.geometry.node_count > 80 || avgSeg < 1.5;
}
