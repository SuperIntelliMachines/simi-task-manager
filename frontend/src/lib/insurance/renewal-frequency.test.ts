import { describe, expect, it } from "vitest";
import {
  formatRenewalFrequencyLabel,
  RENEWAL_FREQUENCY_DEFAULT,
  validateRenewalFrequency,
} from "../insurance/renewal-frequency";

describe("renewal-frequency", () => {
  it("defaults to yearly", () => {
    expect(RENEWAL_FREQUENCY_DEFAULT).toBe("yearly");
  });

  it("formats renewal frequency labels", () => {
    expect(formatRenewalFrequencyLabel("monthly")).toBe("Monthly");
    expect(formatRenewalFrequencyLabel("half_yearly")).toBe("Half-Yearly");
    expect(formatRenewalFrequencyLabel(null)).toBe("Yearly");
    expect(formatRenewalFrequencyLabel("")).toBe("Yearly");
  });

  it("validates renewal frequency selection", () => {
    expect(validateRenewalFrequency("")).toBe("Please select a renewal frequency.");
    expect(validateRenewalFrequency("yearly")).toBeNull();
    expect(validateRenewalFrequency("invalid")).toBe("Please select a renewal frequency.");
  });
});
