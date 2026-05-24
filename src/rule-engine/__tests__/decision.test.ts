import { describe, it, expect } from "vitest";
import { getDecision } from "../decision.js";
import type { Issue } from "../types.js";

function issue(partial: Partial<Issue> & Pick<Issue, "id" | "severity">): Issue {
  return {
    category: "geometry",
    confidence: 0.8,
    title: "t",
    detail: "d",
    source: "s",
    suggested_action: "a",
    ...partial,
  };
}

describe("getDecision", () => {
  it("returns FIX_BEFORE_STITCH when any critical issue", () => {
    const d = getDecision({
      issues: [
        issue({ id: "a", severity: "critical" }),
        issue({ id: "b", severity: "low" }),
      ],
    });
    expect(d.status).toBe("FIX_BEFORE_STITCH");
    expect(d.reason).toBe("Critical issues detected");
  });

  it("returns CAUTION when any high severity", () => {
    const d = getDecision({
      issues: [issue({ id: "x", severity: "high" })],
    });
    expect(d.status).toBe("CAUTION");
  });

  it("returns CAUTION when at least one medium", () => {
    const d = getDecision({
      issues: [issue({ id: "m", severity: "medium" })],
    });
    expect(d.status).toBe("CAUTION");
  });

  it("returns SAFE_TO_TEST when only low issues", () => {
    const d = getDecision({
      issues: [issue({ id: "l", severity: "low" })],
    });
    expect(d.status).toBe("SAFE_TO_TEST");
  });

  it("returns SAFE_TO_TEST when no issues", () => {
    expect(getDecision({ issues: [] }).status).toBe("SAFE_TO_TEST");
  });
});
