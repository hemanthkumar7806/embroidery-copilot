import { getDecision } from "./decision.js";
import { classifyFailure } from "../decision-engine/classifier.js";
import { analyzeGaps } from "./gap-tracker.js";
import {
  buildDecision as buildStateAwareDecision,
  type Decision,
} from "../decision-engine/decision/buildDecision.js";
import { normalizeDesignReport } from "../decision-engine/normalize/normalizeDesignReport.js";
import { detectStateRisk } from "../decision-engine/state/detectStateRisk.js";
import { detectMismatch } from "../decision-engine/state/detectMismatch.js";
import {
  scoreCauses,
  type ScoredCause,
} from "../decision-engine/decision/scoreCauses.js";
import { selectTopCause } from "../decision-engine/decision/selectTopCause.js";
import { validateDecision } from "../decision-engine/decision/validateDecision.js";
import {
  getEntryCount,
  getSuccessRate,
} from "./feedback.js";
import { geometryRules } from "./categories/geometry.js";
import { parameterRules } from "./categories/parameters.js";
import { structureRules } from "./categories/structure.js";
import { routingRules } from "./categories/routing.js";
import { exportRules } from "./categories/export.js";
import { physicalRules } from "./categories/physical.js";
import { performanceRules } from "./categories/performance.js";
import { systemRules } from "./categories/system.js";
import type {
  Category,
  DesignReport,
  DryRunEvaluation,
  Issue,
  Rule,
  RuleEngineOptions,
  RuleEngineResult,
  Severity,
} from "./types.js";
import type { RootCause } from "../decision-engine/root-cause.js";

function toConfidenceTier(value: number): "low" | "medium" | "high" | "certain" {
  if (value >= 0.98) return "certain";
  if (value >= 0.8) return "high";
  if (value >= 0.5) return "medium";
  return "low";
}

function toRootCause(cause: ScoredCause | null): RootCause | null {
  if (!cause) return null;

  if (cause.type === "STATE_DESYNC") {
    return {
      id: cause.type,
      cause: "Object has inconsistent internal state",
      action:
        "Select the object, run Path > Break Apart, remove extra parts, then Path > Combine and reapply satin",
      confidence: "high",
    };
  }

  if (cause.type === "INCONSISTENT_BEHAVIOR" || cause.type === "CORRUPTED_PATH_STATE") {
    return {
      id: cause.type,
      cause: "Hidden SVG or Ink/Stitch state is causing inconsistent behavior",
      action:
        "Select the object, run Path > Break Apart, remove extra parts, then Path > Combine and reapply satin",
      confidence: "high",
    };
  }

  if (cause.type === "NARROW_GEOMETRY") {
    return {
      id: cause.type,
      cause: "Geometry is too narrow for stitching",
      action: "Increase width or switch to running stitch",
      confidence: "medium",
    };
  }

  if (cause.ruleIssue) {
    return {
      id: cause.ruleIssue.id,
      cause: cause.ruleIssue.title,
      action: cause.ruleIssue.suggested_action,
      confidence: toConfidenceTier(cause.confidence),
    };
  }

  return {
    id: cause.type,
    cause: cause.type,
    action: "Fix the detected issue in the selected object",
    confidence: toConfidenceTier(cause.confidence),
  };
}

export const ALL_RULES: Rule[] = [
  ...geometryRules,
  ...parameterRules,
  ...structureRules,
  ...routingRules,
  ...exportRules,
  ...physicalRules,
  ...performanceRules,
  ...systemRules,
];

export const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function emptyBySeverity(): Record<Severity, number> {
  return { critical: 0, high: 0, medium: 0, low: 0 };
}

function emptyByCategory(): Record<Category, number> {
  return {
    geometry: 0,
    parameters: 0,
    structure: 0,
    routing: 0,
    export: 0,
    physical: 0,
    performance: 0,
  };
}

function downgradeSeverity(s: Severity): Severity {
  switch (s) {
    case "critical":
      return "high";
    case "high":
      return "medium";
    case "medium":
      return "low";
    default:
      return "low";
  }
}

function applyFeedbackAdjustments(issues: Issue[]): void {
  for (const issue of issues) {
    const n = getEntryCount(issue.id);
    const rate = getSuccessRate(issue.id);
    if (n >= 5 && rate < 0.4) {
      issue.severity = downgradeSeverity(issue.severity);
      issue.adjustment_note = `Severity reduced: success rate ${(rate * 100).toFixed(0)}% across ${n} feedback samples`;
    }
  }
}

function buildSummary(issues: Issue[]): RuleEngineResult["summary"] {
  const by_severity = emptyBySeverity();
  const by_category = emptyByCategory();
  for (const i of issues) {
    by_severity[i.severity]++;
    by_category[i.category]++;
  }
  let highest_risk_category: Category | null = null;
  let bestCount = 0;
  for (const c of Object.keys(by_category) as Category[]) {
    if (by_category[c] > bestCount) {
      bestCount = by_category[c];
      highest_risk_category = c;
    }
  }
  if (issues.length === 0) highest_risk_category = null;
  return {
    total: issues.length,
    by_severity,
    by_category,
    highest_risk_category,
  };
}

export function getRuleById(id: string): Rule | undefined {
  return ALL_RULES.find((r) => r.id === id);
}

export function getAllRules(): Rule[] {
  return ALL_RULES;
}

export function runRuleEngine(
  report: DesignReport,
  options: RuleEngineOptions = {},
): RuleEngineResult {
  const minConfidence = options.minConfidence ?? 0.5;
  const dryRun = options.dryRun === true;

  const evaluations: DryRunEvaluation[] = [];

  const issues: Issue[] = [];

  for (const rule of ALL_RULES) {
    const skipped = rule.skipWhen?.(report) ?? false;
    const meetsConfidenceThreshold = rule.confidence >= minConfidence;
    const checkResult = skipped ? false : rule.check(report);
    const fired = !skipped && meetsConfidenceThreshold && checkResult;

    evaluations.push({
      rule_id: rule.id,
      fired,
      skipped,
      meetsConfidenceThreshold,
      confidence: rule.confidence,
    });

    if (fired) {
      let severity: Severity = rule.severity;
      if (rule.id === "over_detailed_path") {
        const avg = report.geometry.avg_segment_length_mm;
        if (avg !== null && avg !== undefined && avg < 0.3) {
          severity = "high";
        }
      }
      const issue: Issue = {
        id: rule.id,
        category: rule.category,
        severity,
        confidence: rule.confidence,
        title: rule.title,
        detail: rule.detail(report),
        source: rule.source,
        suggested_action: rule.suggested_action,
      };
      if (rule.group !== undefined) issue.group = rule.group;
      if (rule.evidence !== undefined) issue.evidence = rule.evidence(report);
      issues.push(issue);
    }
  }

  issues.sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);

  applyFeedbackAdjustments(issues);

  const summary = buildSummary(issues);
  const classification = classifyFailure(report, issues);
  const normalized = normalizeDesignReport(report);
  const stateRisks = detectStateRisk(normalized);
  const mismatchIssues = detectMismatch(normalized);
  const scoredCauses = scoreCauses({
    ruleIssues: issues,
    stateRisks,
    mismatchIssues,
  });
  const scoredRootCause = selectTopCause(scoredCauses);
  const rootCause = toRootCause(scoredRootCause);
  const strictDecision: Decision = buildStateAwareDecision(scoredRootCause);
  const detailedDecision = validateDecision(strictDecision);
  if (process.env.DEBUG_ROOT_CAUSE === "1") {
    console.log("ISSUES:", issues);
    console.log("REPORT META:", report.meta ?? null);
    console.log("STATE RISKS:", stateRisks);
    console.log("MISMATCH ISSUES:", mismatchIssues);
    console.log("SCORED CAUSES:", scoredCauses);
    console.log("ROOT CAUSE:", rootCause);
    console.log(
      "CONFIDENCE:",
      rootCause ? rootCause.confidence : null,
    );
    console.log("ISSUE IDS:", issues.map((i) => i.id));
  }
  if (process.env.DEBUG_ROOT_CAUSE === "1") {
    console.log("DETAILED DECISION:", detailedDecision);
  }

  const gaps = analyzeGaps(
    report,
    { issues, dryRunEvaluations: evaluations },
    ALL_RULES,
  );

  const decision = getDecision({ issues });

  return {
    issues,
    classification,
    root_cause: rootCause,
    detailed_decision: detailedDecision,
    summary,
    gaps,
    dryRunEvaluations: dryRun ? evaluations : undefined,
    decision,
  };
}
