import type { ClassificationResult } from "../decision-engine/classifier.js";
import type { RootCause } from "../decision-engine/root-cause.js";
import type { Decision } from "../decision-engine/decision/buildDecision.js";

export type Category =
  | "geometry"
  | "parameters"
  | "structure"
  | "routing"
  | "export"
  | "physical"
  | "performance";

export type Severity = "critical" | "high" | "medium" | "low";

export interface DesignReport {
  meta?: {
    symptom?: string | null;
  };
  geometry: {
    node_count: number;
    path_count: number;
    bounding_box: { w: number; h: number } | null;
    has_open_paths: boolean | null;
    open_path_count?: number | null;
    overlap_ratio: number | null;
    path_length_mm?: number | null;
    avg_segment_length_mm?: number | null;
    min_dimension_mm?: number | null;
  };
  summary: {
    total_path_length_mm?: number | null;
    avg_segment_length_global?: number | null;
    hidden_layer_count?: number | null;
  };
  parameters: {
    row_spacing_mm: number | null;
    stitch_length_mm: number | null;
    pull_compensation_mm: number | null;
    density_value: number | null;
  };
  structure: {
    layer_count: number;
    has_hidden_layers: boolean;
    has_underlay: boolean;
    stitch_types: string[];
    element_count: number;
  };
  routing: {
    jump_stitch_count: number | null;
    trim_count: number | null;
    color_change_count: number | null;
    estimated_stitch_count: number | null;
    has_short_runs: boolean | null;
  };
  export: {
    format: string | null;
    software_version: string | null;
    has_metadata: boolean;
  };
  physical: {
    fabric_type: string | null;
    hoop_size_mm: { w: number; h: number } | null;
    machine_type: string | null;
  };
}

export interface Issue {
  id: string;
  category: Category;
  severity: Severity;
  confidence: number;
  title: string;
  detail: string;
  source: string;
  suggested_action: string;
  adjustment_note?: string;
  group?: string;
  evidence?: Record<string, unknown>;
}

export interface Rule {
  id: string;
  category: Category;
  severity: Severity;
  confidence: number;
  fields: string[];
  skipWhen?: (report: DesignReport) => boolean;
  check: (report: DesignReport) => boolean;
  title: string;
  detail: (report: DesignReport) => string;
  source: string;
  suggested_action: string;
  group?: string;
  evidence?: (report: DesignReport) => Record<string, unknown>;
}

export interface RuleEngineOptions {
  minConfidence?: number;
  dryRun?: boolean;
}

export interface DryRunEvaluation {
  rule_id: string;
  fired: boolean;
  skipped: boolean;
  meetsConfidenceThreshold: boolean;
  confidence: number;
}

export interface GapReport {
  unchecked_fields: string[];
  low_confidence_rules: string[];
  missing_physical_data: string[];
  soft_rules: string[];
  skipped_rules: string[];
}

export type DecisionStatus =
  | "SAFE_TO_TEST"
  | "CAUTION"
  | "FIX_BEFORE_STITCH";

export interface EngineDecision {
  status: DecisionStatus;
  reason: string;
}

export interface RuleEngineResult {
  issues: Issue[];
  classification: ClassificationResult;
  root_cause: RootCause | null;
  detailed_decision: Decision;
  summary: {
    total: number;
    by_severity: Record<Severity, number>;
    by_category: Record<Category, number>;
    highest_risk_category: Category | null;
  };
  gaps: GapReport;
  dryRunEvaluations?: DryRunEvaluation[];
  decision: EngineDecision;
}
