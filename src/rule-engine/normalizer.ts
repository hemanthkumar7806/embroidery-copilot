/**
 * Aggregates bridge `get_design_report` elements[] into a single DesignReport.
 * Unknown metrics use null — not 0 — so rules can skip instead of false positives.
 */

import type { DesignReport } from "./types.js";

export interface BridgeElement {
  id: string;
  stitch_type: string;
  params: Record<string, unknown>;
  geometry?: Record<string, unknown>;
  node_count?: number;
  segment_count?: number;
  path_length_mm?: number | null;
  avg_segment_length_mm?: number | null;
  min_dimension_mm?: number | null;
}

export interface BridgeSummary {
  total_path_length_mm?: number | null;
  avg_segment_length_global?: number | null;
  open_path_count?: number | null;
}

export interface BridgeOutput {
  elements: BridgeElement[];
  summary?: BridgeSummary | null;
}

function num(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number.parseFloat(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

const UNDERLAY_PARAM_KEYS = [
  "fill_underlay",
  "contour_underlay",
  "zigzag_underlay",
  "center_walk_underlay",
  "edge_walk_underlay",
  "satin_underlay",
] as const;

function paramsIndicateUnderlay(p: Record<string, unknown>): boolean {
  for (const k of UNDERLAY_PARAM_KEYS) {
    const v = p[k];
    if (v === true) return true;
    if (typeof v === "string") {
      const s = v.trim().toLowerCase();
      if (s && s !== "none" && s !== "false" && s !== "0") return true;
    }
  }
  return false;
}

/** stroke + manual_stitch → running (Ink/Stitch manual running stitch). */
export function resolveStitchType(el: BridgeElement): string {
  const st = (el.stitch_type || "").toLowerCase();
  if (st === "stroke") {
    const m = el.params?.stroke_method;
    if (typeof m === "string" && m.toLowerCase() === "manual_stitch")
      return "running";
  }
  return el.stitch_type;
}

function collectStitchLengthMm(p: Record<string, unknown>): number | null {
  const candidates = [
    num(p.max_stitch_length_mm),
    num(p.min_stitch_length_mm),
    num(p.stitch_length_mm),
    num(p.running_stitch_length_mm),
  ].filter((v): v is number => v !== null && v > 0);
  if (candidates.length === 0) return null;
  return Math.min(...candidates);
}

export function normalizeDesignReport(bridge: BridgeOutput): DesignReport {
  const elements = bridge.elements ?? [];
  let nodeTotal = 0;
  let hasUnderlay = false;
  const rowVals: number[] = [];
  const stitchLenVals: number[] = [];
  const pullVals: number[] = [];
  let densityProxy: number | null = null;

  for (const el of elements) {
    const nc = el.node_count ?? num(el.geometry?.node_count);
    if (nc !== null && nc > 0) nodeTotal += nc;

    const p = el.params;
    if (p && typeof p === "object") {
      const row = num(p.row_spacing_mm);
      if (row !== null && row > 0) rowVals.push(row);
      const sl = collectStitchLengthMm(p);
      if (sl !== null) stitchLenVals.push(sl);
      const pc = num(p.pull_compensation_mm);
      if (pc !== null) pullVals.push(pc);
      if (paramsIndicateUnderlay(p)) hasUnderlay = true;
      const expand = num(p.expand_mm);
      if (expand !== null && expand > 0) {
        const d = Math.min(1, expand / 8);
        densityProxy = densityProxy === null ? d : Math.max(densityProxy, d);
      }
      if (row !== null && row > 0) {
        const d = Math.min(1, 0.5 / row);
        densityProxy = densityProxy === null ? d : Math.max(densityProxy, d);
      }
    }
  }

  const stitch_types = [
    ...new Set(elements.map((e) => resolveStitchType(e))),
  ];

  const row_spacing_mm =
    rowVals.length > 0 ? Math.min(...rowVals) : null;
  const stitch_length_mm =
    stitchLenVals.length > 0 ? Math.min(...stitchLenVals) : null;
  const pull_compensation_mm =
    pullVals.length > 0 ? Math.max(...pullVals) : null;

  const estimated_stitch_count =
    nodeTotal > 0 && stitch_length_mm !== null
      ? Math.round(nodeTotal * 1.2)
      : null;

  let pathLenSum = 0;
  let pathLenKnown = 0;
  const avgSegs: number[] = [];
  const minDims: number[] = [];
  for (const el of elements) {
    const pl = num(el.path_length_mm);
    if (pl !== null && pl > 0) {
      pathLenSum += pl;
      pathLenKnown += 1;
    }
    const av = num(el.avg_segment_length_mm);
    if (av !== null && av > 0) avgSegs.push(av);
    const md = num(el.min_dimension_mm);
    if (md !== null && md > 0) minDims.push(md);
  }

  const bridgeSummary = bridge.summary ?? null;
  const totalPathMm =
    bridgeSummary?.total_path_length_mm != null &&
    typeof bridgeSummary.total_path_length_mm === "number"
      ? bridgeSummary.total_path_length_mm
      : pathLenKnown > 0
        ? pathLenSum
        : null;
  const minAvgSeg =
    avgSegs.length > 0 ? Math.min(...avgSegs) : null;
  const minDimMm =
    minDims.length > 0 ? Math.min(...minDims) : null;

  const openPathCount = bridgeSummary
    ? num(bridgeSummary.open_path_count)
    : null;
  const hasOpenPaths: boolean | null =
    openPathCount !== null ? openPathCount > 0 : null;

  return {
    geometry: {
      node_count: nodeTotal,
      path_count: elements.length,
      bounding_box: null,
      has_open_paths: hasOpenPaths,
      open_path_count: openPathCount,
      overlap_ratio: null,
      path_length_mm: totalPathMm,
      avg_segment_length_mm: minAvgSeg,
      min_dimension_mm: minDimMm,
    },
    summary: {
      total_path_length_mm: totalPathMm,
      avg_segment_length_global:
        bridgeSummary?.avg_segment_length_global != null
          ? bridgeSummary.avg_segment_length_global
          : null,
    },
    parameters: {
      row_spacing_mm,
      stitch_length_mm,
      pull_compensation_mm,
      density_value: densityProxy,
    },
    structure: {
      layer_count: 1,
      has_hidden_layers: false,
      has_underlay: hasUnderlay,
      stitch_types,
      element_count: elements.length,
    },
    routing: {
      jump_stitch_count: null,
      trim_count: null,
      color_change_count: null,
      estimated_stitch_count,
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
}
