import { describe, it, expect } from "vitest";
import {
  runRuleEngine,
  getAllRules,
  getRuleById,
  ALL_RULES,
} from "../runner.js";
import type { DesignReport } from "../types.js";

const minimal: DesignReport = {
  geometry: {
    node_count: 0,
    path_count: 0,
    bounding_box: null,
    has_open_paths: null,
    open_path_count: null,
    overlap_ratio: null,
    path_length_mm: null,
    avg_segment_length_mm: null,
    min_dimension_mm: null,
  },
  summary: {
    total_path_length_mm: null,
    avg_segment_length_global: null,
  },
  parameters: {
    row_spacing_mm: null,
    stitch_length_mm: null,
    pull_compensation_mm: null,
    density_value: null,
  },
  structure: {
    layer_count: 0,
    has_hidden_layers: false,
    has_underlay: false,
    stitch_types: [],
    element_count: 0,
  },
  routing: {
    jump_stitch_count: null,
    trim_count: null,
    color_change_count: null,
    estimated_stitch_count: null,
    has_short_runs: null,
  },
  export: {
    format: null,
    software_version: null,
    has_metadata: false,
  },
  physical: {
    fabric_type: null,
    hoop_size_mm: null,
    machine_type: null,
  },
};

describe("runner", () => {
  it("getAllRules matches ALL_RULES length", () => {
    expect(getAllRules()).toBe(ALL_RULES);
    expect(getAllRules().length).toBeGreaterThan(0);
  });
  it("getRuleById finds geometry rule", () => {
    expect(getRuleById("high_node_count")?.category).toBe("geometry");
  });
  it("runRuleEngine returns structured result", () => {
    const r = runRuleEngine(minimal);
    expect(Array.isArray(r.issues)).toBe(true);
    expect(r.classification).toBeDefined();
    expect(r.root_cause).toBeDefined();
    expect(r.detailed_decision).toBeDefined();
    expect(r.summary.total).toBe(r.issues.length);
    expect(r.gaps).toBeDefined();
    expect(r.decision).toBeDefined();
    expect(r.decision.reason).toMatch(/\S/);
    expect(r.decision.status).toBe("FIX_BEFORE_STITCH");
  });

  it("uses scoring and picks the highest-ranked cause", () => {
    const r = runRuleEngine({
      ...minimal,
      geometry: {
        ...minimal.geometry,
        node_count: 120,
        avg_segment_length_mm: 0.1,
        min_dimension_mm: 2.0,
      },
      structure: {
        ...minimal.structure,
        element_count: 5,
      },
    });
    expect(r.root_cause?.id).toBe("no_stitch_types_detected");
    expect(r.root_cause?.cause).toBe("No stitch types detected");
  });
});
