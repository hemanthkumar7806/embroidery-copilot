import type { ScoredCause } from "./scoreCauses.js";

export function resolveRootCause(scored: ScoredCause[]): ScoredCause | null {
  if (!scored.length) return null;
  return scored[0];
}
