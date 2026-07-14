import { describe, expect, it } from "vitest";
import {
  MOBILE_NUMBER_ERROR,
  normalizeMobileNumber,
  sanitizeMobileNumberInput,
  validateMobileNumber,
} from "./policy-mobile";

describe("policy-mobile", () => {
  it("sanitizes non-numeric characters and caps length", () => {
    expect(sanitizeMobileNumberInput("98-7654-3210")).toBe("9876543210");
    expect(sanitizeMobileNumberInput("9198765432109999")).toBe("919876543210999");
  });

  it("allows optional leading plus for international numbers", () => {
    expect(sanitizeMobileNumberInput("+919121529697")).toBe("+919121529697");
    expect(sanitizeMobileNumberInput("+91 91215 29697")).toBe("+919121529697");
    expect(normalizeMobileNumber("+91 91215 29697")).toBe("+919121529697");
  });

  it("accepts valid mobile numbers", () => {
    expect(validateMobileNumber("9876543210")).toBeNull();
    expect(validateMobileNumber("919876543210")).toBeNull();
    expect(validateMobileNumber("+919121529697")).toBeNull();
  });

  it("rejects invalid mobile numbers", () => {
    expect(validateMobileNumber("98765abcde")).toBe(MOBILE_NUMBER_ERROR);
    expect(validateMobileNumber("123456789")).toBe(MOBILE_NUMBER_ERROR);
    expect(validateMobileNumber("1234567890123456")).toBe(MOBILE_NUMBER_ERROR);
    expect(validateMobileNumber("")).toBe(MOBILE_NUMBER_ERROR);
    expect(validateMobileNumber("+")).toBe(MOBILE_NUMBER_ERROR);
  });
});
