import { describe, it, expect } from "vitest";
import { performanceRules } from "../categories/performance.js";
import type { DesignReport } from "../types.js";

function base(): DesignReport {
  return {
    geometry: {
      node_count: 150,
      path_count: 10,
      bounding_box: { w: 50, h: 50 },
      has_open_paths: false,
      open_path_count: null,
      overlap_ratio: 0.1,
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
      stitch_length_mm: 1.4,
      pull_compensation_mm: 0.2,
      density_value: 0.3,
    },
    structure: {
      layer_count: 1,
      has_hidden_layers: false,
      has_underlay: true,
      stitch_types: ["fill"],
      element_count: 3,
    },
    routing: {
      jump_stitch_count: 0,
      trim_count: 0,
      color_change_count: 0,
      estimated_stitch_count: 1000,
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
}

function find(id: string) {
  return performanceRules.find((x) => x.id === id)!;
}

describe("density_interaction_risk", () => {
  it("fires when all conditions hold", () => {
    const rep = base();
    expect(find("density_interaction_risk").check(rep)).toBe(true);
  });
  it("does not fire when node_count <= 120", () => {
    const rep = base();
    rep.geometry.node_count = 100;
    expect(find("density_interaction_risk").check(rep)).toBe(false);
  });
  it("does not fire when element_count <= 1", () => {
    const rep = base();
    rep.structure.element_count = 1;
    rep.geometry.node_count = 200;
    expect(find("density_interaction_risk").check(rep)).toBe(false);
  });
});

describe("stitch_count_risk", () => {
  it("fires when path length / stitch length exceeds 3000", () => {
    const rep = base();
    rep.geometry.path_length_mm = 9000;
    rep.parameters.stitch_length_mm = 2;
    expect(find("stitch_count_risk").check(rep)).toBe(true);
  });
  it("does not fire when path or stitch missing or estimate low", () => {
    expect(find("stitch_count_risk").check(base())).toBe(false);
    const rep = base();
    rep.geometry.path_length_mm = 3000;
    rep.parameters.stitch_length_mm = 2;
    expect(find("stitch_count_risk").check(rep)).toBe(false);
  });
});

describe("global_complexity_risk", () => {
  it("fires when total path long and global avg segment short", () => {
    const rep = base();
    rep.summary.total_path_length_mm = 2500;
    rep.summary.avg_segment_length_global = 0.5;
    expect(find("global_complexity_risk").check(rep)).toBe(true);
  });
  it("does not fire when summary fields null or thresholds not met", () => {
    expect(find("global_complexity_risk").check(base())).toBe(false);
    const rep = base();
    rep.summary.total_path_length_mm = 1500;
    rep.summary.avg_segment_length_global = 0.5;
    expect(find("global_complexity_risk").check(rep)).toBe(false);
  });
});
