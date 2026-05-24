import { DECISION_CONFIG } from "../../config/decisionConfig.js";
import type { ScoredCause } from "./scoreCauses.js";

export function selectTopCause(scored: ScoredCause[]): ScoredCause | null {
  if (!scored.length) return null;

  const top = scored[0];
  if (top.score < DECISION_CONFIG.HIGH_CONFIDENCE) {
    return null;
  }

  return top;
}
