import { describe, expect, it } from "vitest";

import { normalizeLeadingZeros } from "./NormalizedNumberInput";

describe("normalizeLeadingZeros", () => {
  it("strips leading zeros while preserving a single zero", () => {
    expect(normalizeLeadingZeros("024")).toBe("24");
    expect(normalizeLeadingZeros("028")).toBe("28");
    expect(normalizeLeadingZeros("001")).toBe("1");
    expect(normalizeLeadingZeros("005")).toBe("5");
    expect(normalizeLeadingZeros("000")).toBe("0");
    expect(normalizeLeadingZeros("0")).toBe("0");
  });

  it("preserves empty input for editing", () => {
    expect(normalizeLeadingZeros("")).toBe("");
    expect(normalizeLeadingZeros("   ")).toBe("");
  });
});
