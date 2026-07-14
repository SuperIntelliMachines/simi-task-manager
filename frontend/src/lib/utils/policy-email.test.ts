import { describe, expect, it } from "vitest";
import { validateEmail } from "./policy-email";

describe("validateEmail", () => {
  it("allows empty optional email", () => {
    expect(validateEmail("")).toBeNull();
    expect(validateEmail("   ")).toBeNull();
  });

  it("accepts valid email addresses", () => {
    expect(validateEmail("user@example.com")).toBeNull();
    expect(validateEmail("  holder@domain.co.in  ")).toBeNull();
  });

  it("rejects invalid email addresses", () => {
    expect(validateEmail("not-an-email")).toBeTruthy();
    expect(validateEmail("missing@domain")).toBeTruthy();
  });
});
