import { describe, expect, it } from "vitest";
import { runRuleEngine } from "../../../rule-engine/runner.js";
import type { DesignReport } from "../../../rule-engine/types.js";

function baseReport(): DesignReport {
  return {
    geometry: {
      node_count: 10,
      path_count: 1,
      bounding_box: null,
      has_open_paths: false,
      open_path_count: 0,
      overlap_ratio: null,
      path_length_mm: null,
      avg_segment_length_mm: 1.2,
      min_dimension_mm: 2.0,
    },
    summary: {
      total_path_length_mm: null,
      avg_segment_length_global: null,
      hidden_layer_count: 0,
    },
    parameters: {
      row_spacing_mm: 0.4,
      stitch_length_mm: 2.5,
      pull_compensation_mm: 0.2,
      density_value: 0.4,
    },
    structure: {
      layer_count: 1,
      has_hidden_layers: false,
      has_underlay: true,
      stitch_types: ["satin"],
      element_count: 2,
    },
    routing: {
      jump_stitch_count: 2,
      trim_count: 1,
      color_change_count: 1,
      estimated_stitch_count: 200,
      has_short_runs: false,
    },
    export: {
      format: "pes",
      software_version: "1.0",
      has_metadata: true,
    },
    physical: {
      fabric_type: "cotton",
      hoop_size_mm: { w: 100, h: 100 },
      machine_type: "single",
    },
  };
}

describe("state-aware decision flow", () => {
  it("detects mismatch for similar geometry with different stitch types", () => {
    const report = {
      ...baseReport(),
      elements: [
        {
          id: "a",
          node_count: 30,
          min_segment_length: 1.2,
          stitch_type: "satin",
          attrs: {},
          d: "M 0 0 L 10 0",
        },
        {
          id: "b",
          node_count: 30,
          min_segment_length: 1.2,
          stitch_type: "stroke",
          attrs: {},
          d: "M 0 1 L 10 1",
        },
      ],
    } as DesignReport & { elements: unknown[] };

    const result = runRuleEngine(report);
    expect(result.root_cause?.id).toBe("INCONSISTENT_BEHAVIOR");
    expect(result.detailed_decision.main_problem).toBe(
      "Object has inconsistent internal state",
    );
  });

  it("detects state desync when stroke has inkstitch attrs", () => {
    const report = {
      ...baseReport(),
      elements: [
        {
          id: "x",
          node_count: 20,
          min_segment_length: 1.0,
          stitch_type: "stroke",
          attrs: { "inkstitch:satin_column": "true" },
          d: "M 0 0 L 5 0",
        },
      ],
    } as DesignReport & { elements: unknown[] };

    const result = runRuleEngine(report);
    expect(result.root_cause?.id).toBe("STATE_DESYNC");
  });

  it("falls back to clean decision when no causes are detected", () => {
    const report = {
      ...baseReport(),
      structure: {
        ...baseReport().structure,
        stitch_types: ["fill"],
      },
      elements: [
        {
          id: "clean",
          node_count: 20,
          min_segment_length: 1.5,
          stitch_type: "fill",
          attrs: {},
          d: "M 0 0 L 20 0",
        },
      ],
    } as DesignReport & { elements: unknown[] };

    const result = runRuleEngine(report);
    expect(result.detailed_decision.main_problem).toBe("No file-level issue detected");
  });

  it("returns geometry-driven decision when geometry issue is strong", () => {
    const report = {
      ...baseReport(),
      geometry: {
        ...baseReport().geometry,
        min_dimension_mm: 0.6,
      },
      elements: [
        {
          id: "geo",
          node_count: 40,
          min_segment_length: 1.0,
          stitch_type: "satin",
          attrs: {},
          d: "M 0 0 L 10 0",
        },
      ],
    } as DesignReport & { elements: unknown[] };

    const result = runRuleEngine(report);
    expect(result.root_cause?.id).toBe("narrow_geometry_stitch_mismatch");
    expect(result.detailed_decision.main_problem).toBe("narrow_geometry_stitch_mismatch");
  });
});
