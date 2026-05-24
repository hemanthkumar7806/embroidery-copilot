import type { Rule } from "../types.js";

const MACHINE_FORMATS = ["dst", "pes", "jef", "vp3", "exp", "hus"];

export const exportRules: Rule[] = [
  {
    id: "missing_metadata",
    category: "export",
    severity: "low",
    confidence: 0.5,
    fields: ["export.has_metadata"],
    title: "Missing metadata",
    source: "production tracking best practice",
    suggested_action: "Add design metadata in Ink/Stitch before export",
    check: (r) => !r.export.has_metadata,
    detail: () =>
      "Design metadata (name, size, thread count) is missing. Metadata is important for production tracking.",
  },
  {
    id: "unsupported_format",
    category: "export",
    severity: "high",
    confidence: 0.85,
    fields: ["export.format"],
    skipWhen: (r) => r.export.format === null,
    title: "Possibly unsupported export format",
    source: "docs/sources/ricoma/chroma-supported-file-types.md; common machine formats",
    suggested_action:
      "Export to DST, PES, JEF, or VP3 depending on your machine brand",
    check: (r) => {
      const f = r.export.format!.toLowerCase();
      return !MACHINE_FORMATS.includes(f);
    },
    detail: (r) =>
      `Format "${r.export.format}" may not be supported by all machines.`,
  },
];
