import type { EngineDecision, RuleEngineResult } from "./types.js";

export function getDecision(
  result: Pick<RuleEngineResult, "issues">,
): EngineDecision {
  const issues = result.issues;
  const hasCritical = issues.some((i) => i.severity === "critical");
  const hasHigh = issues.some((i) => i.severity === "high");
  const mediumCount = issues.filter((i) => i.severity === "medium").length;

  if (hasCritical) {
    return {
      status: "FIX_BEFORE_STITCH",
      reason: "Critical issues detected",
    };
  }

  if (hasHigh || mediumCount >= 1) {
    return {
      status: "CAUTION",
      reason: "Moderate risks detected",
    };
  }

  return {
    status: "SAFE_TO_TEST",
    reason: "No critical issues detected",
  };
}
