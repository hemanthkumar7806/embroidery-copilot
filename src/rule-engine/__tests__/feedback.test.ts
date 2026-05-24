import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, readFileSync, rmSync, existsSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import {
  logFeedback,
  getSuccessRate,
  getEntryCount,
  getRulesWithLowSuccessRate,
} from "../feedback.js";
import { runRuleEngine } from "../runner.js";
import type { DesignReport } from "../types.js";

let tmpDir: string;

beforeEach(() => {
  tmpDir = mkdtempSync(join(tmpdir(), "rule-engine-fb-"));
  process.env.RULE_ENGINE_FEEDBACK_PATH = join(tmpDir, "feedback.json");
});

afterEach(() => {
  delete process.env.RULE_ENGINE_FEEDBACK_PATH;
  rmSync(tmpDir, { recursive: true, force: true });
});

describe("feedback", () => {
  it("logFeedback writes a valid JSONL line", () => {
    logFeedback({
      timestamp: "2026-01-01T00:00:00.000Z",
      rule_id: "test_rule",
      design_hash: "abc",
      issue_was_real: true,
    });
    const path = process.env.RULE_ENGINE_FEEDBACK_PATH!;
    expect(existsSync(path)).toBe(true);
    const line = readFileSync(path, "utf-8").trim();
    const row = JSON.parse(line) as { rule_id: string };
    expect(row.rule_id).toBe("test_rule");
  });

  it("getSuccessRate returns 1.0 with no entries", () => {
    expect(getSuccessRate("any")).toBe(1);
  });

  it("getSuccessRate returns correct rate with 3 true, 2 false entries", () => {
    for (let i = 0; i < 3; i++) {
      logFeedback({
        timestamp: new Date().toISOString(),
        rule_id: "r1",
        design_hash: `d${i}`,
        issue_was_real: true,
      });
    }
    for (let i = 0; i < 2; i++) {
      logFeedback({
        timestamp: new Date().toISOString(),
        rule_id: "r1",
        design_hash: `b${i}`,
        issue_was_real: false,
      });
    }
    expect(getSuccessRate("r1")).toBeCloseTo(0.6);
  });

  it("getRulesWithLowSuccessRate ignores rules with < 5 entries", () => {
    for (let i = 0; i < 3; i++) {
      logFeedback({
        timestamp: new Date().toISOString(),
        rule_id: "low_sample",
        design_hash: `x${i}`,
        issue_was_real: false,
      });
    }
    expect(getRulesWithLowSuccessRate(0.4)).not.toContain("low_sample");
  });

  it("getRulesWithLowSuccessRate includes rule with 5+ bad samples", () => {
    for (let i = 0; i < 5; i++) {
      logFeedback({
        timestamp: new Date().toISOString(),
        rule_id: "bad_rule",
        design_hash: `y${i}`,
        issue_was_real: false,
      });
    }
    expect(getRulesWithLowSuccessRate(0.4)).toContain("bad_rule");
  });
});

describe("runner feedback integration", () => {
  const openPathReport: DesignReport = {
    geometry: {
      node_count: 10,
      path_count: 1,
      bounding_box: { w: 10, h: 10 },
      has_open_paths: true,
      open_path_count: null,
      overlap_ratio: 0,
      path_length_mm: null,
      avg_segment_length_mm: null,
      min_dimension_mm: null,
    },
    summary: {
      total_path_length_mm: null,
      avg_segment_length_global: null,
    },
    parameters: {
      row_spacing_mm: 0.4,
      stitch_length_mm: 2.5,
      pull_compensation_mm: 0.2,
      density_value: 0.3,
    },
    structure: {
      layer_count: 1,
      has_hidden_layers: false,
      has_underlay: true,
      stitch_types: ["fill"],
      element_count: 1,
    },
    routing: {
      jump_stitch_count: 0,
      trim_count: 0,
      color_change_count: 0,
      estimated_stitch_count: 100,
      has_short_runs: false,
    },
    export: {
      format: "dst",
      software_version: "1",
      has_metadata: true,
    },
    physical: {
      fabric_type: "cotton",
      hoop_size_mm: { w: 200, h: 200 },
      machine_type: null,
    },
  };

  it("runner downgrades severity when rate < 0.4 and count >= 5", () => {
    for (let i = 0; i < 5; i++) {
      logFeedback({
        timestamp: new Date().toISOString(),
        rule_id: "open_paths_present",
        design_hash: `h${i}`,
        issue_was_real: false,
      });
    }
    expect(getEntryCount("open_paths_present")).toBe(5);
    expect(getSuccessRate("open_paths_present")).toBe(0);
    const result = runRuleEngine(openPathReport);
    const issue = result.issues.find((i) => i.id === "open_paths_present");
    expect(issue).toBeDefined();
    expect(issue!.severity).toBe("medium");
    expect(issue!.adjustment_note).toContain("Severity reduced");
  });

  it("runner does NOT downgrade when count < 5", () => {
    for (let i = 0; i < 3; i++) {
      logFeedback({
        timestamp: new Date().toISOString(),
        rule_id: "open_paths_present",
        design_hash: `k${i}`,
        issue_was_real: false,
      });
    }
    const result = runRuleEngine(openPathReport);
    const issue = result.issues.find((i) => i.id === "open_paths_present");
    expect(issue?.severity).toBe("high");
    expect(issue?.adjustment_note).toBeUndefined();
  });
});
