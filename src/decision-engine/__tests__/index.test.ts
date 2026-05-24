import { describe, expect, it } from "vitest";
import { buildDecision } from "../index.js";
import { classifyFailure, type ClassificationResult } from "../classifier.js";
import { resolveRootCause } from "../cause-mapper.js";
import type { DesignReport, Issue } from "../../rule-engine/types.js";
import type { RootCause } from "../root-cause.js";

function issue(partial: Partial<Issue> & Pick<Issue, "id" | "severity">): Issue {
  return {
    id: partial.id,
    severity: partial.severity,
    category: partial.category ?? "geometry",
    confidence: partial.confidence ?? 0.9,
    title: partial.title ?? partial.id,
    detail: partial.detail ?? "detail",
    source: partial.source ?? "rule",
    suggested_action: partial.suggested_action ?? "action",
    group: partial.group,
    evidence: partial.evidence,
  };
}

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
      stitch_length_mm: 2.5,
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

function classification(
  partial: Partial<ClassificationResult> = {},
): ClassificationResult {
  return {
    type: "unknown",
    confidence: "low",
    reason: "No strong signal detected",
    ...partial,
  };
}

describe("buildDecision", () => {
  function rootCause(partial: Partial<RootCause> = {}): RootCause {
    return {
      id: "duplicate_nodes_overlap",
      cause: "Two nodes are overlapping at the same position",
      action: "Use node tool, zoom in, and delete overlapping node",
      confidence: "high",
      ...partial,
    };
  }

  it("returns file_fix mode for high-confidence root cause", () => {
    const result = buildDecision({
      report: report(),
      issues: [issue({ id: "open_paths_present", severity: "high" })],
      classification: classification({ type: "geometry", confidence: "high" }),
      rootCause: rootCause(),
    });

    expect(result.verdict).toBe("⚠️ File-level issue detected");
    expect(result.mode).toBe("file_fix");
    expect(result.main_problem.id).toBe("duplicate_nodes_overlap");
    expect(result.next_action).toBe("Use node tool, zoom in, and delete overlapping node");
  });

  it("returns physical_check fallback for medium-confidence root cause", () => {
    const result = buildDecision({
      report: report(),
      issues: [issue({ id: "open_paths_present", severity: "high" })],
      classification: classification({ type: "geometry", confidence: "medium" }),
      rootCause: rootCause({ confidence: "medium" }),
    });

    expect(result.mode).toBe("physical_check");
    expect(result.main_problem.id).toBe("no_file_issue");
    expect(result.checklist?.length).toBe(5);
    expect(result.next_action).toBe("Check fabric, stabilizer, and machine setup");
  });

  it("returns physical_check fallback when rootCause is null", () => {
    const result = buildDecision({
      report: report(),
      issues: [issue({ id: "open_paths_present", severity: "high" })],
      classification: classification(),
      rootCause: null,
    });

    expect(result.mode).toBe("physical_check");
    expect(result.verdict).toBe("✅ No critical file-level issues detected");
  });

  it("uses short explanation for duplicate_nodes_overlap", () => {
    const result = buildDecision({
      report: report(),
      issues: [issue({ id: "open_paths_present", severity: "high" })],
      classification: classification(),
      rootCause: rootCause({ id: "duplicate_nodes_overlap" }),
    });
    expect(result.explanation).toBe(
      "Overlapping nodes trigger false border crossing errors.",
    );
  });

  it("uses short explanation for svg_structure_invalid", () => {
    const result = buildDecision({
      report: report(),
      issues: [issue({ id: "no_stitch_types_detected", severity: "high" })],
      classification: classification({ type: "structure", confidence: "high" }),
      rootCause: rootCause({
        id: "svg_structure_invalid",
        cause: "SVG uses non-path elements (clones/groups) not recognized by Ink/Stitch",
        action: "Convert all objects to path and ungroup everything",
        confidence: "certain",
      }),
    });
    expect(result.explanation).toBe(
      "Design exists visually but is not converted into stitchable paths.",
    );
  });
});

describe("classifyFailure", () => {
  it("prefers structure over geometry when both signals exist", () => {
    const result = classifyFailure(
      report({
        geometry: {
          node_count: 10,
          path_count: 0,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 0.2,
          min_dimension_mm: 0.8,
        },
        structure: {
          layer_count: 1,
          has_hidden_layers: false,
          has_underlay: false,
          stitch_types: [],
          element_count: 0,
        },
      }),
      [],
    );
    expect(result.type).toBe("structure");
  });

  it("classifies as parameter for mixed stitch types signal", () => {
    const result = classifyFailure(
      report({
        structure: {
          layer_count: 1,
          has_hidden_layers: false,
          has_underlay: false,
          stitch_types: ["running", "satin"],
          element_count: 21,
        },
      }),
      [],
    );
    expect(result).toEqual({
      type: "parameter",
      confidence: "medium",
      reason: "Mixed stitch types suggest param inconsistency",
    });
  });

  it("classifies as routing when jump stitch data is missing", () => {
    const result = classifyFailure(
      report({
        export: { format: "pes", software_version: null, has_metadata: false },
        geometry: {
          node_count: 1,
          path_count: 1,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 1.2,
          min_dimension_mm: 2.5,
        },
      }),
      [],
    );
    expect(result.type).toBe("routing");
  });

  it("returns unknown when no strong signal is found", () => {
    const result = classifyFailure(
      report({
        export: { format: "pes", software_version: null, has_metadata: false },
        geometry: {
          node_count: 1,
          path_count: 1,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 1.2,
          min_dimension_mm: 2.5,
        },
        routing: {
          jump_stitch_count: 2,
          trim_count: null,
          color_change_count: null,
          estimated_stitch_count: null,
          has_short_runs: null,
        },
      }),
      [],
    );
    expect(result).toEqual({
      type: "unknown",
      confidence: "low",
      reason: "No strong signal detected",
    });
  });
});

describe("resolveRootCause", () => {
  it("prefers svg_structure_invalid before geometry fragility mappings", () => {
    const result = resolveRootCause(
      report({
        geometry: {
          node_count: 10,
          path_count: 1,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 0.2,
          min_dimension_mm: 0.8,
        },
        structure: {
          layer_count: 1,
          has_hidden_layers: false,
          has_underlay: false,
          stitch_types: ["satin"],
          element_count: 0,
        },
      }),
      [issue({ id: "open_paths_present", severity: "medium" })],
    );
    expect(result?.id).toBe("svg_structure_invalid");
  });

  it("maps trim_missing when jump stitch routing data is missing", () => {
    const result = resolveRootCause(
      report({
        geometry: {
          node_count: 30,
          path_count: 2,
          bounding_box: null,
          has_open_paths: true,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 0.8,
          min_dimension_mm: 0.7,
        },
      }),
      [issue({ id: "open_paths_present", severity: "high" })],
    );
    expect(result?.id).toBe("trim_missing");
  });

  it("maps duplicate_nodes_overlap from cross/intersection issue id + move symptom", () => {
    const result = resolveRootCause(
      report({
        meta: {
          symptom: "border crosses itself error disappears after slight move",
        },
        geometry: {
          node_count: 30,
          path_count: 2,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: null,
          path_length_mm: null,
          avg_segment_length_mm: 0.9,
          min_dimension_mm: 1.2,
        },
      }),
      [
        issue({
          id: "border_crosses_itself",
          severity: "high",
          title: "Border crosses itself",
          detail: "Path border intersects itself",
        }),
      ],
    );
    expect(result?.id).toBe("duplicate_nodes_overlap");
  });

  it("returns null when no mapping matches", () => {
    const result = resolveRootCause(
      report({
        export: {
          format: "dst",
          software_version: "1.0",
          has_metadata: true,
        },
        geometry: {
          node_count: 10,
          path_count: 2,
          bounding_box: null,
          has_open_paths: false,
          overlap_ratio: 0.1,
          path_length_mm: null,
          avg_segment_length_mm: 1.2,
          min_dimension_mm: 2.5,
        },
        parameters: {
          row_spacing_mm: 0.4,
          stitch_length_mm: 2.8,
          pull_compensation_mm: 0.3,
          density_value: 0.4,
        },
        structure: {
          layer_count: 1,
          has_hidden_layers: false,
          has_underlay: true,
          stitch_types: ["fill"],
          element_count: 5,
        },
        routing: {
          jump_stitch_count: 3,
          trim_count: 1,
          color_change_count: 1,
          estimated_stitch_count: 1000,
          has_short_runs: false,
        },
        physical: {
          fabric_type: "cotton",
          hoop_size_mm: { w: 100, h: 100 },
          machine_type: "single",
        },
      }),
      [],
    );
    expect(result).toBeNull();
  });
});
