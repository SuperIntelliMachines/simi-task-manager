import { describe, expect, it } from "vitest";

import { parsePolicyListFilter, policyListPath } from "./policy-list-navigation";

describe("policyListPath", () => {
  it("builds paths for dashboard card navigation", () => {
    expect(policyListPath()).toBe("/app/insurance/policies");
    expect(policyListPath("active")).toBe("/app/insurance/policies?filter=active");
    expect(policyListPath("due")).toBe("/app/insurance/policies?filter=due");
    expect(policyListPath("expiring")).toBe("/app/insurance/policies?filter=expiring");
    expect(policyListPath("expiring_soon")).toBe("/app/insurance/policies?filter=expiring_soon");
    expect(policyListPath("expired")).toBe("/app/insurance/policies?filter=expired");
  });
});

describe("parsePolicyListFilter", () => {
  it("accepts known filter values only", () => {
    expect(parsePolicyListFilter("due")).toBe("due");
    expect(parsePolicyListFilter("expiring_soon")).toBe("expiring_soon");
    expect(parsePolicyListFilter("active-other")).toBeNull();
    expect(parsePolicyListFilter(null)).toBeNull();
  });
});
