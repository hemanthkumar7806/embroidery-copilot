import { describe, it, expect } from "vitest";
import { parameterRules } from "../categories/parameters.js";
import type { DesignReport } from "../types.js";

function base(): DesignReport {
  return {
    geometry: {
      node_count: 100,
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
      stitch_length_mm: 2.5,
      pull_compensation_mm: 0.2,
      density_value: 0.3,
    },
    structure: {
      layer_count: 1,
      has_hidden_layers: false,
      has_underlay: true,
      stitch_types: ["fill"],
      element_count: 5,
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
  return parameterRules.find((x) => x.id === id)!;
}

describe("parameter rules", () => {
  it("row_spacing_too_low triggers", () => {
    const rep = base();
    rep.parameters.row_spacing_mm = 0.2;
    expect(find("row_spacing_too_low").check(rep)).toBe(true);
  });
  it("row_spacing_too_low does not trigger", () => {
    expect(find("row_spacing_too_low").check(base())).toBe(false);
  });

  it("row_spacing_too_high triggers", () => {
    const rep = base();
    rep.parameters.row_spacing_mm = 0.6;
    expect(find("row_spacing_too_high").check(rep)).toBe(true);
  });
  it("row_spacing_too_high does not trigger", () => {
    expect(find("row_spacing_too_high").check(base())).toBe(false);
  });

  it("stitch_length_too_short triggers", () => {
    const rep = base();
    rep.parameters.stitch_length_mm = 1.0;
    expect(find("stitch_length_too_short").check(rep)).toBe(true);
  });
  it("stitch_length_too_short does not trigger", () => {
    expect(find("stitch_length_too_short").check(base())).toBe(false);
  });

  it("stitch_length_too_long triggers", () => {
    const rep = base();
    rep.parameters.stitch_length_mm = 7;
    expect(find("stitch_length_too_long").check(rep)).toBe(true);
  });
  it("stitch_length_too_long does not trigger", () => {
    expect(find("stitch_length_too_long").check(base())).toBe(false);
  });

  it("pull_compensation_missing triggers", () => {
    const rep = base();
    rep.parameters.pull_compensation_mm = 0;
    rep.structure.stitch_types = ["fill"];
    expect(find("pull_compensation_missing").check(rep)).toBe(true);
  });
  it("pull_compensation_missing does not trigger when compensated", () => {
    expect(find("pull_compensation_missing").check(base())).toBe(false);
  });

  it("extreme_density triggers", () => {
    const rep = base();
    rep.parameters.density_value = 0.8;
    expect(find("extreme_density").check(rep)).toBe(true);
  });
  it("extreme_density does not trigger", () => {
    expect(find("extreme_density").check(base())).toBe(false);
  });
});
