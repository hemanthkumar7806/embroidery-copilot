import { describe, it, expect } from "vitest";
import {
  normalizeDesignReport,
  resolveStitchType,
} from "../normalizer.js";

describe("resolveStitchType", () => {
  it("maps stroke + manual_stitch to running", () => {
    expect(
      resolveStitchType({
        id: "x",
        stitch_type: "stroke",
        params: { stroke_method: "manual_stitch" },
      }),
    ).toBe("running");
  });
  it("keeps other stroke methods as stroke", () => {
    expect(
      resolveStitchType({
        id: "x",
        stitch_type: "stroke",
        params: { stroke_method: "zigzag" },
      }),
    ).toBe("stroke");
  });
});

describe("normalizeDesignReport", () => {
  it("aggregates node counts and stitch types from elements", () => {
    const report = normalizeDesignReport({
      elements: [
        {
          id: "a",
          stitch_type: "fill",
          params: { row_spacing_mm: "0.4", pull_compensation_mm: 0.2 },
          node_count: 100,
        },
        {
          id: "b",
          stitch_type: "satin",
          params: {},
          node_count: 50,
        },
      ],
    });
    expect(report.geometry.node_count).toBe(150);
    expect(report.geometry.has_open_paths).toBeNull();
    expect(report.geometry.open_path_count).toBeNull();
    expect(report.geometry.path_length_mm).toBeNull();
    expect(report.geometry.avg_segment_length_mm).toBeNull();
    expect(report.geometry.min_dimension_mm).toBeNull();
    expect(report.summary.total_path_length_mm).toBeNull();
    expect(report.summary.avg_segment_length_global).toBeNull();
    expect(report.structure.element_count).toBe(2);
    expect(new Set(report.structure.stitch_types)).toEqual(
      new Set(["fill", "satin"]),
    );
  });

  it("detects underlay from inkstitch-style params", () => {
    const report = normalizeDesignReport({
      elements: [
        {
          id: "x",
          stitch_type: "fill",
          params: { fill_underlay: "true" },
        },
      ],
    });
    expect(report.structure.has_underlay).toBe(true);
  });

  it("maps running_stitch_length_mm into parameters.stitch_length_mm", () => {
    const report = normalizeDesignReport({
      elements: [
        {
          id: "r",
          stitch_type: "stroke",
          params: {
            stroke_method: "manual_stitch",
            running_stitch_length_mm: "2.0",
          },
        },
      ],
    });
    expect(report.parameters.stitch_length_mm).toBe(2);
    expect(report.structure.stitch_types).toContain("running");
  });

  it("uses null for row_spacing when absent", () => {
    const report = normalizeDesignReport({
      elements: [
        {
          id: "s",
          stitch_type: "satin",
          params: {},
        },
      ],
    });
    expect(report.parameters.row_spacing_mm).toBeNull();
  });

  it("leaves routing null when bridge has no routing data", () => {
    const report = normalizeDesignReport({ elements: [] });
    expect(report.routing.estimated_stitch_count).toBeNull();
    expect(report.routing.jump_stitch_count).toBeNull();
  });

  it("sets estimated_stitch_count from node count and stitch length", () => {
    const report = normalizeDesignReport({
      elements: [
        {
          id: "a",
          stitch_type: "fill",
          params: { stitch_length_mm: 2 },
          node_count: 100,
        },
      ],
    });
    expect(report.geometry.node_count).toBe(100);
    expect(report.parameters.stitch_length_mm).toBe(2);
    expect(report.routing.estimated_stitch_count).toBe(Math.round(100 * 1.2));
  });

  it("maps summary.open_path_count to has_open_paths and open_path_count", () => {
    const report = normalizeDesignReport({
      elements: [
        {
          id: "a",
          stitch_type: "fill",
          params: {},
          node_count: 10,
        },
      ],
      summary: {
        open_path_count: 3,
        total_path_length_mm: null,
        avg_segment_length_global: null,
      },
    });
    expect(report.geometry.has_open_paths).toBe(true);
    expect(report.geometry.open_path_count).toBe(3);
  });

  it("leaves estimated_stitch_count null when stitch length is absent", () => {
    const report = normalizeDesignReport({
      elements: [
        {
          id: "a",
          stitch_type: "fill",
          params: {},
          node_count: 50,
        },
      ],
    });
    expect(report.routing.estimated_stitch_count).toBeNull();
  });
});
