import { describe, expect, it } from "vitest";

import { getFollowupCustomerName } from "./followup-display";

describe("getFollowupCustomerName", () => {
  it("prefers customerName from API", () => {
    expect(getFollowupCustomerName({ customerName: "Sandy", contact_name: "Other" })).toBe("Sandy");
  });

  it("falls back to contact_name", () => {
    expect(getFollowupCustomerName({ contact_name: "Tony" })).toBe("Tony");
  });

  it("returns Unnamed Customer when no name fields exist", () => {
    expect(getFollowupCustomerName({})).toBe("Unnamed Customer");
    expect(getFollowupCustomerName(null)).toBe("Unnamed Customer");
  });
});
