import type { Decision } from "./buildDecision.js";

export function validateDecision(decision: Decision): Decision {
  if (!decision.main_problem || !decision.next_action) {
    throw new Error("Invalid decision output");
  }

  if (decision.main_problem.includes(",")) {
    throw new Error("Multiple problems detected");
  }

  return decision;
}
