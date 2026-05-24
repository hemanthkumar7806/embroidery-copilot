import type { Issue } from "../../rule-engine/types.js";
import type { MismatchIssue } from "../state/detectMismatch.js";
import type { StateRisk } from "../state/detectStateRisk.js";

export type ScoredCause = {
  type: string;
  score: number;
  confidence: number;
  source: "rule" | "state" | "mismatch";
  ruleIssue?: Issue;
  element?: string;
  elements?: string[];
};

type ScoreInput = {
  ruleIssues: Issue[];
  stateRisks: StateRisk[];
  mismatchIssues: MismatchIssue[];
};

export function scoreCauses({
  ruleIssues,
  stateRisks,
  mismatchIssues,
}: ScoreInput): ScoredCause[] {
  const all: ScoredCause[] = [];

  for (const r of ruleIssues) {
    all.push({
      type: r.id,
      score: r.confidence ?? 0.6,
      confidence: r.confidence ?? 0.6,
      source: "rule",
      ruleIssue: r,
    });
  }

  for (const r of stateRisks) {
    all.push({
      type: r.type,
      score: (r.confidence ?? 0.7) + 0.05,
      confidence: r.confidence,
      source: "state",
      element: r.element,
    });
  }

  for (const m of mismatchIssues) {
    all.push({
      type: m.type,
      score: (m.confidence ?? 0.8) + 0.1,
      confidence: m.confidence,
      source: "mismatch",
      elements: m.elements,
    });
  }

  return all.sort((a, b) => b.score - a.score);
}
