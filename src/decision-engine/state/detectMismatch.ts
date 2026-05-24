import type { DesignElement, NormalizedDesignReport } from "../normalize/normalizeDesignReport.js";

export type MismatchIssue = {
  type: "INCONSISTENT_BEHAVIOR";
  elements: string[];
  confidence: number;
};

function groupBySimilarity(elements: DesignElement[]): DesignElement[][] {
  const map = new Map<string, DesignElement[]>();

  for (const el of elements) {
    const key = `${el.node_count}_${Math.round(el.min_segment_length)}`;
    if (!map.has(key)) map.set(key, []);
    map.get(key)?.push(el);
  }

  return Array.from(map.values());
}

export function detectMismatch(report: NormalizedDesignReport): MismatchIssue[] {
  const issues: MismatchIssue[] = [];
  const groups = groupBySimilarity(report.elements);

  for (const group of groups) {
    const stitchTypes = new Set(group.map((e) => e.stitch_type));
    if (stitchTypes.size > 1 && group.length > 1) {
      issues.push({
        type: "INCONSISTENT_BEHAVIOR",
        elements: group.map((e) => e.id),
        confidence: 0.9,
      });
    }
  }

  return issues;
}
