import { describe, expect, it } from "vitest";
import { formatLoggedInUserDisplayName } from "./user-display";

describe("user-display", () => {
  it("formats an email into a display name", () => {
    expect(formatLoggedInUserDisplayName("uday.kumar@example.com")).toBe("Uday Kumar");
  });

  it("falls back when empty", () => {
    expect(formatLoggedInUserDisplayName("")).toBe("SIMI Insurance");
    expect(formatLoggedInUserDisplayName(undefined)).toBe("SIMI Insurance");
  });
});
