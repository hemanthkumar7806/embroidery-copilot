import type { DesignReport } from "../../rule-engine/types.js";

export type DesignElement = {
  id: string;
  node_count: number;
  subpath_count: number;
  min_segment_length: number;
  stitch_type: "satin" | "stroke" | "fill" | null;
  attrs: Record<string, any>;
  hasInkstitchAttrs: boolean;
  isSingleStrokeVisual: boolean;
  d?: string;
};

export type NormalizedDesignReport = {
  elements: DesignElement[];
};

function countSubpaths(el: { d?: string }): number {
  return el.d?.split("M").length ? el.d.split("M").length - 1 || 1 : 1;
}

function asStitchType(value: unknown): "satin" | "stroke" | "fill" | null {
  if (value === "satin" || value === "stroke" || value === "fill") return value;
  return null;
}

function normalizeElement(raw: Record<string, unknown>, index: number): DesignElement {
  const attrs = (raw.attrs as Record<string, any> | undefined) ?? {};
  const d = typeof raw.d === "string" ? raw.d : undefined;
  const nodeCountRaw = raw.node_count;
  const node_count =
    typeof nodeCountRaw === "number" && Number.isFinite(nodeCountRaw) ? nodeCountRaw : 0;
  const minSegRaw = raw.min_segment_length;
  const min_segment_length =
    typeof minSegRaw === "number" && Number.isFinite(minSegRaw) ? minSegRaw : 0;

  const base: DesignElement = {
    id: typeof raw.id === "string" ? raw.id : `element_${index + 1}`,
    node_count,
    subpath_count: 1,
    min_segment_length,
    stitch_type: asStitchType(raw.stitch_type),
    attrs,
    hasInkstitchAttrs: false,
    isSingleStrokeVisual: false,
    d,
  };

  base.hasInkstitchAttrs = Object.keys(base.attrs || {}).some((k) =>
    k.startsWith("inkstitch:"),
  );
  base.subpath_count = countSubpaths(base);
  base.isSingleStrokeVisual = base.subpath_count === 1 && base.node_count < 50;

  return base;
}

export function normalizeDesignReport(report: DesignReport): NormalizedDesignReport {
  const rawElements = (report as DesignReport & { elements?: Record<string, unknown>[] })
    .elements;

  if (Array.isArray(rawElements) && rawElements.length > 0) {
    return {
      elements: rawElements.map((el, index) => normalizeElement(el, index)),
    };
  }

  const attrs: Record<string, any> = {};
  const stitchType = report.structure.stitch_types[0];
  const pseudo = normalizeElement(
    {
      id: "report_geometry",
      node_count: report.geometry.node_count,
      min_segment_length: report.geometry.avg_segment_length_mm ?? 0,
      stitch_type: asStitchType(stitchType),
      attrs,
      d: "M 0 0",
    },
    0,
  );

  return { elements: [pseudo] };
}
