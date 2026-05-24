import type { Rule } from "../types.js";

export const routingRules: Rule[] = [
  {
    id: "excessive_jump_stitches",
    category: "routing",
    severity: "high",
    confidence: 0.8,
    fields: ["routing.jump_stitch_count"],
    skipWhen: (r) => r.routing.jump_stitch_count === null,
    title: "Excessive jump stitches",
    source: "docs/sources/inkstitch/tutorial-routing.md",
    suggested_action:
      "Re-order stitch elements or use running stitch connectors between nearby objects",
    check: (r) => r.routing.jump_stitch_count! > 30,
    detail: (r) =>
      `${r.routing.jump_stitch_count} jump stitches detected (threshold: 30). Excessive jumps increase production time and visible thread tails.`,
  },
  {
    id: "excessive_color_changes",
    category: "routing",
    severity: "medium",
    confidence: 0.75,
    fields: ["routing.color_change_count"],
    skipWhen: (r) => r.routing.color_change_count === null,
    title: "Excessive color changes",
    source: "production / machine stops",
    suggested_action:
      "Consolidate colors — reorder elements to batch same-color stitching together",
    check: (r) => r.routing.color_change_count! > 10,
    detail: (r) =>
      `${r.routing.color_change_count} color changes (threshold: 10). Each change requires machine stop and operator re-threading.`,
  },
  {
    id: "stitch_count_too_high",
    category: "routing",
    severity: "medium",
    confidence: 0.7,
    fields: ["routing.estimated_stitch_count"],
    skipWhen: (r) => r.routing.estimated_stitch_count === null,
    title: "Stitch count very high",
    source: "production time heuristic",
    suggested_action:
      "Simplify design or reduce fill density to lower stitch count",
    check: (r) => r.routing.estimated_stitch_count! > 15000,
    detail: (r) =>
      `Estimated ${r.routing.estimated_stitch_count!.toLocaleString()} stitches (threshold: 15,000). High stitch count significantly increases production time.`,
  },
  {
    id: "short_run_segments",
    category: "routing",
    severity: "high",
    confidence: 0.78,
    fields: ["routing.has_short_runs"],
    skipWhen: (r) => r.routing.has_short_runs === null,
    title: "Short run segments",
    source: "docs/sources/community/failure-causes.md",
    suggested_action:
      "Minimum 3 stitches per run — merge very short segments with adjacent elements",
    check: (r) => r.routing.has_short_runs === true,
    detail: () =>
      "Short run segments detected (fewer than 3 stitches). Very short runs cause tension issues and thread nesting.",
  },
  {
    id: "trim_count_high",
    category: "routing",
    severity: "low",
    confidence: 0.6,
    fields: ["routing.trim_count"],
    skipWhen: (r) => r.routing.trim_count === null,
    title: "High trim count",
    source: "production efficiency",
    suggested_action:
      "Connect nearby elements with short running stitches instead of trim+jump",
    check: (r) => r.routing.trim_count! > 20,
    detail: (r) =>
      `${r.routing.trim_count} trims detected (threshold: 20). Excessive trims slow production and increase manual cleanup.`,
  },
  {
    id: "zero_stitches",
    category: "routing",
    severity: "critical",
    confidence: 1.0,
    fields: ["routing.estimated_stitch_count"],
    skipWhen: (r) => r.routing.estimated_stitch_count === null,
    title: "Zero stitches",
    source: "docs/sources/inkstitch/params-overview.md",
    suggested_action:
      "Apply Ink/Stitch params to paths via Extensions > Ink/Stitch > Params before simulating",
    check: (r) => r.routing.estimated_stitch_count === 0,
    detail: () =>
      "Zero stitches estimated. No Ink/Stitch params are applied to any design element.",
  },
];
