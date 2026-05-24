import { describe, it, expect } from "vitest";
import { geometryRules } from "../categories/geometry.js";
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
  const r = geometryRules.find((x) => x.id === id)!;
  return r;
}

describe("geometry rules", () => {
  it("high_node_count triggers above threshold", () => {
    const rep = base();
    rep.geometry.node_count = 1200;
    expect(find("high_node_count").check(rep)).toBe(true);
  });
  it("high_node_count does not trigger below threshold", () => {
    const rep = base();
    rep.geometry.node_count = 500;
    expect(find("high_node_count").check(rep)).toBe(false);
  });

  it("open_paths_present triggers when open", () => {
    const rep = base();
    rep.geometry.has_open_paths = true;
    expect(find("open_paths_present").check(rep)).toBe(true);
  });
  it("open_paths_present does not trigger when closed", () => {
    expect(find("open_paths_present").check(base())).toBe(false);
  });

  it("high_overlap_ratio triggers", () => {
    const rep = base();
    rep.geometry.overlap_ratio = 0.5;
    expect(find("high_overlap_ratio").check(rep)).toBe(true);
  });
  it("high_overlap_ratio does not trigger", () => {
    expect(find("high_overlap_ratio").check(base())).toBe(false);
  });

  it("design_exceeds_hoop triggers", () => {
    const rep = base();
    rep.geometry.bounding_box = { w: 300, h: 50 };
    rep.physical.hoop_size_mm = { w: 200, h: 200 };
    expect(find("design_exceeds_hoop").check(rep)).toBe(true);
  });
  it("design_exceeds_hoop does not trigger when fit", () => {
    expect(find("design_exceeds_hoop").check(base())).toBe(false);
  });

  it("too_many_paths triggers", () => {
    const rep = base();
    rep.geometry.path_count = 600;
    expect(find("too_many_paths").check(rep)).toBe(true);
  });
  it("too_many_paths does not trigger", () => {
    expect(find("too_many_paths").check(base())).toBe(false);
  });

  it("running_stitch_density_risk triggers when stitch short and many nodes", () => {
    const rep = base();
    rep.parameters.stitch_length_mm = 1.4;
    rep.geometry.node_count = 90;
    expect(find("running_stitch_density_risk").check(rep)).toBe(true);
  });
  it("running_stitch_density_risk does not trigger when stitch length above 1.5", () => {
    const rep = base();
    rep.parameters.stitch_length_mm = 2;
    rep.geometry.node_count = 200;
    expect(find("running_stitch_density_risk").check(rep)).toBe(false);
  });
  it("running_stitch_density_risk does not trigger when node count at or below 80", () => {
    const rep = base();
    rep.parameters.stitch_length_mm = 1.2;
    rep.geometry.node_count = 80;
    expect(find("running_stitch_density_risk").check(rep)).toBe(false);
  });
  it("running_stitch_density_risk triggers when avg segment short even if nodes at 80", () => {
    const rep = base();
    rep.parameters.stitch_length_mm = 1.2;
    rep.geometry.node_count = 80;
    rep.geometry.avg_segment_length_mm = 0.4;
    expect(find("running_stitch_density_risk").check(rep)).toBe(true);
  });
  it("running_stitch_density_risk does not trigger when density_interaction_risk would apply", () => {
    const rep = base();
    rep.parameters.stitch_length_mm = 1.4;
    rep.geometry.node_count = 150;
    rep.structure.element_count = 3;
    expect(find("running_stitch_density_risk").check(rep)).toBe(false);
  });

  it("over_detailed_path triggers when avg segment below 0.5", () => {
    const rep = base();
    rep.geometry.avg_segment_length_mm = 0.3;
    expect(find("over_detailed_path").check(rep)).toBe(true);
  });
  it("over_detailed_path does not trigger when avg null or high", () => {
    expect(find("over_detailed_path").check(base())).toBe(false);
    const rep = base();
    rep.geometry.avg_segment_length_mm = 0.6;
    expect(find("over_detailed_path").check(rep)).toBe(false);
  });

  it("narrow_geometry_stitch_mismatch triggers for narrow fill", () => {
    const rep = base();
    rep.geometry.min_dimension_mm = 0.5;
    rep.structure.stitch_types = ["fill"];
    expect(find("narrow_geometry_stitch_mismatch").check(rep)).toBe(true);
  });
  it("narrow_geometry_stitch_mismatch triggers for narrow satin", () => {
    const rep = base();
    rep.geometry.min_dimension_mm = 0.5;
    rep.structure.stitch_types = ["satin"];
    expect(find("narrow_geometry_stitch_mismatch").check(rep)).toBe(true);
  });
  it("narrow_geometry_stitch_mismatch does not trigger for running-only or wide min", () => {
    const rep = base();
    rep.geometry.min_dimension_mm = 0.5;
    rep.structure.stitch_types = ["running"];
    expect(find("narrow_geometry_stitch_mismatch").check(rep)).toBe(false);
    const rep2 = base();
    rep2.geometry.min_dimension_mm = 2;
    rep2.structure.stitch_types = ["fill"];
    expect(find("narrow_geometry_stitch_mismatch").check(rep2)).toBe(false);
    expect(find("narrow_geometry_stitch_mismatch").check(base())).toBe(false);
  });
});
