import { describe, it, expect } from "vitest";
import { runRuleEngine, ALL_RULES, CANONICAL_LEAF_PATHS } from "../index.js";
import type { DesignReport } from "../types.js";

// Triggers simulation_freeze_risk, high_complexity_design, excessive_fragmentation (node/path/element load)
const BAD_DESIGN: DesignReport = {
  geometry: {
    node_count: 1450,
    path_count: 600,
    bounding_box: { w: 180, h: 220 },
    has_open_paths: true,
    open_path_count: null,
    overlap_ratio: 0.42,
    path_length_mm: null,
    avg_segment_length_mm: null,
    min_dimension_mm: null,
  },
  summary: {
    total_path_length_mm: null,
    avg_segment_length_global: null,
  },
  parameters: {
    row_spacing_mm: 0.22,
    stitch_length_mm: 1.1,
    pull_compensation_mm: 0,
    density_value: 0.7,
  },
  structure: {
    layer_count: 4,
    has_hidden_layers: true,
    has_underlay: false,
    stitch_types: ["fill", "satin"],
    element_count: 280,
  },
  routing: {
    jump_stitch_count: 55,
    trim_count: 32,
    color_change_count: 12,
    estimated_stitch_count: 18000,
    has_short_runs: true,
  },
  export: {
    format: "svg",
    software_version: "1.0",
    has_metadata: false,
  },
  physical: {
    fabric_type: "jersey",
    hoop_size_mm: { w: 150, h: 150 },
    machine_type: null,
  },
};

const GOOD_DESIGN: DesignReport = {
  geometry: {
    node_count: 200,
    path_count: 30,
    bounding_box: { w: 100, h: 80 },
    has_open_paths: false,
    open_path_count: null,
    overlap_ratio: 0.05,
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
    pull_compensation_mm: 0.25,
    density_value: 0.4,
  },
  structure: {
    layer_count: 2,
    has_hidden_layers: false,
    has_underlay: true,
    stitch_types: ["fill", "running"],
    element_count: 15,
  },
  routing: {
    jump_stitch_count: 5,
    trim_count: 3,
    color_change_count: 2,
    estimated_stitch_count: 4000,
    has_short_runs: false,
  },
  export: {
    format: "dst",
    software_version: "1.2",
    has_metadata: true,
  },
  physical: {
    fabric_type: "cotton",
    hoop_size_mm: { w: 200, h: 200 },
    machine_type: null,
  },
};

function getAt(obj: unknown, path: string): unknown {
  let cur: unknown = obj;
  for (const part of path.split(".")) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

describe("BAD_DESIGN", () => {
  const result = runRuleEngine(BAD_DESIGN);
  it("returns at least 8 issues", () => {
    expect(result.issues.length).toBeGreaterThanOrEqual(8);
  });
  it("decision is FIX_BEFORE_STITCH due to critical issues", () => {
    expect(result.decision.status).toBe("FIX_BEFORE_STITCH");
  });
  it("includes density_interaction_risk and omits running_stitch when interaction covers density", () => {
    const ids = result.issues.map((i) => i.id);
    expect(ids).toContain("density_interaction_risk");
    expect(ids).not.toContain("running_stitch_density_risk");
  });
  it("first issue is critical or high severity", () => {
    const s = result.issues[0]?.severity;
    expect(s === "critical" || s === "high").toBe(true);
  });
  it("includes row_spacing_too_low", () => {
    expect(result.issues.map((i) => i.id)).toContain("row_spacing_too_low");
  });
  it("includes stretchy_fabric_no_underlay", () => {
    expect(result.issues.map((i) => i.id)).toContain(
      "stretchy_fabric_no_underlay",
    );
  });
  it("includes design_exceeds_hoop", () => {
    expect(result.issues.map((i) => i.id)).toContain("design_exceeds_hoop");
  });
  it("includes open_paths_present", () => {
    expect(result.issues.map((i) => i.id)).toContain("open_paths_present");
  });
  it("includes simulation_freeze_risk", () => {
    expect(result.issues.map((i) => i.id)).toContain("simulation_freeze_risk");
  });
  it("includes high_complexity_design", () => {
    expect(result.issues.map((i) => i.id)).toContain("high_complexity_design");
  });
  it("includes excessive_fragmentation", () => {
    expect(result.issues.map((i) => i.id)).toContain("excessive_fragmentation");
  });
  it("simulation_freeze_risk includes group and evidence", () => {
    const issue = result.issues.find((i) => i.id === "simulation_freeze_risk");
    expect(issue?.group).toBe("performance");
    expect(issue?.evidence?.complexity_score).toBeDefined();
    expect(issue?.evidence?.node_count).toBe(1450);
  });
  it("summary.highest_risk_category is set", () => {
    expect(result.summary.highest_risk_category).not.toBeNull();
  });
  it("by_severity.critical >= 1", () => {
    expect(result.summary.by_severity.critical).toBeGreaterThanOrEqual(1);
  });
});

describe("GOOD_DESIGN", () => {
  it("returns zero critical issues", () => {
    const result = runRuleEngine(GOOD_DESIGN);
    expect(result.issues.filter((i) => i.severity === "critical").length).toBe(
      0,
    );
  });
  it("returns no more than 2 issues total", () => {
    const result = runRuleEngine(GOOD_DESIGN);
    expect(result.issues.length).toBeLessThanOrEqual(2);
  });
  it("decision is SAFE_TO_TEST or CAUTION", () => {
    const result = runRuleEngine(GOOD_DESIGN);
    expect(["SAFE_TO_TEST", "CAUTION"]).toContain(result.decision.status);
  });
});

describe("dryRun mode", () => {
  it("returns dryRunEvaluations array", () => {
    const result = runRuleEngine(BAD_DESIGN, { dryRun: true });
    expect(result.dryRunEvaluations).toBeDefined();
    expect(Array.isArray(result.dryRunEvaluations)).toBe(true);
  });
  it("every rule appears in dryRunEvaluations", () => {
    const result = runRuleEngine(BAD_DESIGN, { dryRun: true });
    expect(result.dryRunEvaluations!.length).toBe(ALL_RULES.length);
    const ids = new Set(result.dryRunEvaluations!.map((e) => e.rule_id));
    for (const rule of ALL_RULES) expect(ids.has(rule.id)).toBe(true);
  });
  it("fired rules in dryRunEvaluations match issues array", () => {
    const result = runRuleEngine(BAD_DESIGN, { dryRun: true });
    const firedIds = new Set(
      result.dryRunEvaluations!.filter((e) => e.fired).map((e) => e.rule_id),
    );
    const issueIds = new Set(result.issues.map((i) => i.id));
    expect(firedIds).toEqual(issueIds);
  });
  it("skipped rules have skipped true and fired false", () => {
    const result = runRuleEngine(BAD_DESIGN, { dryRun: true });
    for (const e of result.dryRunEvaluations!) {
      if (e.skipped) {
        expect(e.fired).toBe(false);
      }
    }
  });
});

describe("minConfidence filtering", () => {
  it("runRuleEngine(BAD_DESIGN, { minConfidence: 0.9 }) returns fewer issues than default", () => {
    const def = runRuleEngine(BAD_DESIGN).issues.length;
    const strict = runRuleEngine(BAD_DESIGN, { minConfidence: 0.9 }).issues
      .length;
    expect(strict).toBeLessThan(def);
  });
});

describe("gap tracker", () => {
  it("unchecked_fields does not include fields covered by rules", () => {
    const result = runRuleEngine(BAD_DESIGN);
    expect(result.gaps.unchecked_fields).not.toContain("geometry.node_count");
  });
  it("export.software_version is not in unchecked_fields", () => {
    const result = runRuleEngine(BAD_DESIGN);
    expect(result.gaps.unchecked_fields).not.toContain("export.software_version");
  });
  it("physical.machine_type is in missing_physical_data for BAD_DESIGN", () => {
    const result = runRuleEngine(BAD_DESIGN);
    expect(result.gaps.missing_physical_data).toContain("machine_type");
  });
  it("design_exceeds_hoop appears in skipped_rules when hoop_size_mm is null", () => {
    const rep: DesignReport = {
      ...BAD_DESIGN,
      physical: { ...BAD_DESIGN.physical, hoop_size_mm: null },
    };
    const result = runRuleEngine(rep);
    expect(result.gaps.skipped_rules).toContain("design_exceeds_hoop");
  });
});

describe("canonical leaf paths vs DesignReport", () => {
  it("every field in CANONICAL_LEAF_PATHS is a real DesignReport field", () => {
    const sample = BAD_DESIGN;
    for (const path of CANONICAL_LEAF_PATHS) {
      const v = getAt(sample, path);
      expect(v, path).not.toBeUndefined();
    }
  });
});
