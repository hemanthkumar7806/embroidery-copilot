import type { Rule } from "../types.js";

const STRETCHY = ["jersey", "knit", "stretch", "lycra", "spandex"];

export const physicalRules: Rule[] = [
  {
    id: "fabric_type_unknown",
    category: "physical",
    severity: "low",
    confidence: 0.4,
    fields: ["physical.fabric_type"],
    title: "Fabric type unknown",
    source: "docs/rules/issue-checker-cross-reference.md (fabric-dependent thresholds)",
    suggested_action:
      "Specify fabric type so appropriate thresholds can be applied",
    check: (r) => r.physical.fabric_type === null,
    detail: () =>
      "Fabric type not specified. Density, pull compensation, and underlay thresholds all vary by fabric.",
  },
  {
    id: "hoop_size_not_set",
    category: "physical",
    severity: "low",
    confidence: 0.4,
    fields: ["physical.hoop_size_mm"],
    title: "Hoop size not set",
    source: "hoop boundary checks",
    suggested_action: "Set hoop size to enable boundary checking",
    check: (r) => r.physical.hoop_size_mm === null,
    detail: () =>
      "Hoop size not specified. Cannot check whether design fits the hoop.",
  },
  {
    id: "stretchy_fabric_no_underlay",
    category: "physical",
    severity: "critical",
    confidence: 0.88,
    fields: ["physical.fabric_type", "structure.has_underlay"],
    skipWhen: (r) => r.physical.fabric_type === null,
    title: "Stretchy fabric without underlay",
    source: "docs/sources/community/fabric-presets.md",
    suggested_action:
      "Add cutaway stabilizer and grid underlay for all stretchy fabric designs",
    check: (r) => {
      const f = r.physical.fabric_type!.toLowerCase();
      return STRETCHY.includes(f) && !r.structure.has_underlay;
    },
    detail: (r) =>
      `Fabric type "${r.physical.fabric_type}" is stretchy but no underlay is set. Stretchy fabric with no underlay will severely distort.`,
  },
];
