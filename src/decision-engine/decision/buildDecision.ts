import type { ScoredCause } from "./scoreCauses.js";

/**
 * This system does NOT try to be always correct.
 * It tries to give the safest useful next action.
 */
export type Decision = {
  main_problem: string;
  next_action: string;
  explanation: string;
};

export function buildDecision(cause: ScoredCause | null): Decision {
  if (!cause) {
    return {
      main_problem: "No file-level issue detected",
      next_action:
        "Check fabric, stabilizer, thread tension, needle, and machine settings",
      explanation:
        "The file structure looks correct, so the issue is likely in the physical setup",
    };
  }

  if (
    cause.type === "STATE_DESYNC" ||
    cause.type === "INCONSISTENT_BEHAVIOR" ||
    cause.type === "CORRUPTED_PATH_STATE"
  ) {
    return {
      main_problem: "Object has inconsistent internal state",
      next_action:
        "Select the object, run Path > Break Apart, remove extra parts, then Path > Combine and reapply satin",
      explanation: "Hidden SVG or Ink/Stitch state is causing inconsistent behavior",
    };
  }

  if (cause.type === "NARROW_GEOMETRY") {
    return {
      main_problem: "Geometry is too narrow for stitching",
      next_action: "Increase width or switch to running stitch",
      explanation: "Very small widths cannot form stable stitches",
    };
  }

  return {
    main_problem: cause.type,
    next_action: "Fix the detected issue in the selected object",
    explanation: "The file contains a structural issue affecting stitching",
  };
}
