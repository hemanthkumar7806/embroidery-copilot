export {
  runRuleEngine,
  getAllRules,
  getRuleById,
  ALL_RULES,
  SEVERITY_ORDER,
} from "./runner.js";

export { getDecision } from "./decision.js";

export { densityInteractionRiskFires } from "./categories/performance.js";

export type {
  Category,
  Severity,
  DesignReport,
  Issue,
  Rule,
  RuleEngineOptions,
  DryRunEvaluation,
  RuleEngineResult,
  GapReport,
  DecisionStatus,
  EngineDecision,
} from "./types.js";

export {
  normalizeDesignReport,
  resolveStitchType,
  type BridgeOutput,
  type BridgeElement,
} from "./normalizer.js";

export {
  analyzeGaps,
  CANONICAL_LEAF_PATHS,
  flattenReportPaths,
} from "./gap-tracker.js";

export {
  logFeedback,
  getSuccessRate,
  getEntryCount,
  getRulesWithLowSuccessRate,
  readAllFeedback,
  getFeedbackFilePath,
  type FeedbackEntry,
} from "./feedback.js";
