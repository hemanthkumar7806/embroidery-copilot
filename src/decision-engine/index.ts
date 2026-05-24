import type { DesignReport, Issue } from "../rule-engine/types.js";
import type { ClassificationResult } from "./classifier.js";
import type { RootCause } from "./root-cause.js";

export type DecisionInput = {
  report: DesignReport;
  issues: Issue[];
  classification: ClassificationResult;
  rootCause: RootCause | null;
};

type ConfidenceTier = "low" | "medium" | "high" | "certain";

type MainProblem = {
  id: string;
  confidence: ConfidenceTier;
  detail: string;
};

export type DecisionOutput = {
  verdict: string;
  main_problem: MainProblem;
  next_action: string;
  explanation: string;
  checklist?: string[];
  mode: "file_fix" | "physical_check";
  supporting_problems: string[];
};

function isHighConfidence(rootCause: RootCause | null): boolean {
  return !!(
    rootCause &&
    (rootCause.confidence === "high" || rootCause.confidence === "certain")
  );
}

function generateShortExplanation(rootCause: RootCause): string {
  if (rootCause.id === "duplicate_nodes_overlap") {
    return "Overlapping nodes trigger false border crossing errors.";
  }

  if (rootCause.id === "svg_structure_invalid") {
    return "Design exists visually but is not converted into stitchable paths.";
  }

  return "Detected from geometry and design signals.";
}

export function buildDecision(input: DecisionInput): DecisionOutput {
  if (isHighConfidence(input.rootCause)) {
    const rootCause = input.rootCause as RootCause;
    return {
      verdict: "⚠️ File-level issue detected",
      main_problem: {
        id: rootCause.id,
        detail: rootCause.cause,
        confidence: rootCause.confidence,
      },
      next_action: rootCause.action,
      explanation: generateShortExplanation(rootCause),
      mode: "file_fix",
      supporting_problems: input.issues.slice(0, 2).map((i) => i.id),
    };
  }

  return {
    verdict: "✅ No critical file-level issues detected",
    main_problem: {
      id: "no_file_issue",
      detail: "Design appears structurally valid",
      confidence: "low",
    },
    next_action: "Check fabric, stabilizer, and machine setup",
    explanation:
      "The file looks correct, so the issue is likely caused by physical setup rather than design.",
    checklist: [
      "Verify fabric type (knit vs woven)",
      "Use appropriate stabilizer (cutaway for stretch)",
      "Check thread tension",
      "Ensure needle is correct and not worn",
      "Reduce machine speed if needed",
    ],
    mode: "physical_check",
    supporting_problems: input.issues.slice(0, 2).map((i) => i.id),
  };
}
