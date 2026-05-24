import { describe, expect, it } from "vitest";
import { abstractSignals } from "../signal-abstraction.js";
import type { DesignReport, Issue } from "../../rule-engine/types.js";

function report(partial: Partial<DesignReport> = {}): DesignReport {
  return {
    geometry: {
      node_count: 0,
      path_count: 0,
      bounding_box: null,
      has_open_paths: false,
      overlap_ratio: null,
      path_length_mm: null,
      avg_segment_length_mm: null,
      min_dimension_mm: 2.5,
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
      layer_count: 1,
      has_hidden_layers: false,
      has_underlay: false,
      stitch_types: [],
      element_count: 1,
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
    ...partial,
  };
}

function issue(partial: Partial<Issue> & Pick<Issue, "id">): Issue {
  return {
    id: partial.id,
    category: partial.category ?? "geometry",
    severity: partial.severity ?? "high",
    confidence: partial.confidence ?? 0.9,
    title: partial.title ?? partial.id,
    detail: partial.detail ?? "detail",
    source: partial.source ?? "rule",
    suggested_action: partial.suggested_action ?? "action",
    group: partial.group,
    evidence: partial.evidence,
  };
}

describe("abstractSignals", () => {
  it("returns invalid_geometry_overlap for cross-like issue signal", () => {
    const result = abstractSignals({
      report: report(),
      issues: [issue({ id: "border_crosses_itself", title: "Border crosses itself" })],
    });

    expect(result?.id).toBe("invalid_geometry_overlap");
    expect(result?.confidence).toBe("high");
  });

  it("returns not_converted_to_path when structure is empty with nodes", () => {
    const result = abstractSignals({
      report: report({
        geometry: {
          node_count: 12,
          path_count: 1,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 1.0,
          min_dimension_mm: 2.5,
        },
        structure: {
          layer_count: 1,
          has_hidden_layers: false,
          has_underlay: false,
          stitch_types: [],
          element_count: 0,
        },
      }),
      issues: [],
    });

    expect(result?.id).toBe("not_converted_to_path");
  });

  it("returns over_detailed_path for tiny average segment and high nodes", () => {
    const result = abstractSignals({
      report: report({
        geometry: {
          node_count: 150,
          path_count: 1,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 0.4,
          min_dimension_mm: 2.5,
        },
      }),
      issues: [],
    });

    expect(result?.id).toBe("over_detailed_path");
    expect(result?.confidence).toBe("medium");
  });

  it("applies rule priority and returns first match", () => {
    const result = abstractSignals({
      report: report({
        geometry: {
          node_count: 150,
          path_count: 1,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 0.1,
          min_dimension_mm: 0,
        },
        structure: {
          layer_count: 1,
          has_hidden_layers: false,
          has_underlay: false,
          stitch_types: [],
          element_count: 0,
        },
      }),
      issues: [],
    });

    expect(result?.id).toBe("invalid_geometry_overlap");
  });

  it("returns null when no abstraction rule matches", () => {
    const result = abstractSignals({
      report: report({
        geometry: {
          node_count: 10,
          path_count: 1,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 1.2,
          min_dimension_mm: 2.5,
        },
      }),
      issues: [],
    });
    expect(result).toBeNull();
  });
});
