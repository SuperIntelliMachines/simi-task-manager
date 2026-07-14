import { describe, expect, it } from "vitest";
import {
  addDaysToDisplayDate,
  displayDateFromIso,
  formatDisplayDateInput,
  isoDateFromDisplay,
  isValidDisplayDate,
  todayDisplayDate,
  validateDisplayDate,
  validateRenewalExpiryDate,
  RENEWAL_EXPIRY_MUST_BE_LATER_MESSAGE,
} from "./date-display";

describe("date-display", () => {
  it("converts between DD-MM-YYYY and ISO date", () => {
    expect(isoDateFromDisplay("13-06-2026")).toBe("2026-06-13");
    expect(displayDateFromIso("2026-06-13")).toBe("13-06-2026");
  });

  it("rejects invalid display dates", () => {
    expect(isValidDisplayDate("13-06-yyyy")).toBe(false);
    expect(isValidDisplayDate("13-06-222222")).toBe(false);
    expect(isValidDisplayDate("15-06-20266")).toBe(false);
    expect(isValidDisplayDate("01-01-2026123")).toBe(false);
    expect(isValidDisplayDate("31-02-2026")).toBe(false);
    expect(isValidDisplayDate("")).toBe(false);
  });

  it("returns clear validation messages for invalid dates", () => {
    expect(validateDisplayDate("15-06-2026")).toBeNull();
    expect(validateDisplayDate("01-01-222222")).toBe("Year must be exactly 4 digits.");
    expect(validateDisplayDate("15-06-20266")).toBe("Year must be exactly 4 digits.");
    expect(validateDisplayDate("01-01-2026123")).toBe("Year must be exactly 4 digits.");
    expect(validateDisplayDate("31-02-2026")).toBe("Please enter a valid calendar date.");
    expect(validateDisplayDate("99-99-9999")).toMatch(/valid calendar date|between 1900 and 2100/);
    expect(validateDisplayDate("15/06/2026")).toMatch(/Invalid date format/);
  });

  it("formats manual date input as DD-MM-YYYY while typing", () => {
    expect(formatDisplayDateInput("1")).toBe("1");
    expect(formatDisplayDateInput("15")).toBe("15");
    expect(formatDisplayDateInput("156")).toBe("15-6");
    expect(formatDisplayDateInput("1506")).toBe("15-06");
    expect(formatDisplayDateInput("15062026")).toBe("15-06-2026");
    expect(formatDisplayDateInput("15/06/2026")).toBe("15-06-2026");
    expect(formatDisplayDateInput("15-06-2026123")).toBe("15-06-2026");
    expect(formatDisplayDateInput("01012027")).toBe("01-01-2027");
  });

  it("adds days in display format", () => {
    expect(addDaysToDisplayDate("13-06-2026", 5)).toBe("18-06-2026");
  });

  it("formats today as DD-MM-YYYY", () => {
    expect(todayDisplayDate()).toMatch(/^\d{2}-\d{2}-\d{4}$/);
  });

  it("validates renewal expiry against current expiry", () => {
    expect(validateRenewalExpiryDate("18-07-2027", "18-07-2026")).toBeNull();
    expect(validateRenewalExpiryDate("18-07-2026", "18-07-2026")).toBe(
      RENEWAL_EXPIRY_MUST_BE_LATER_MESSAGE,
    );
    expect(validateRenewalExpiryDate("17-06-2026", "18-07-2026")).toBe(
      RENEWAL_EXPIRY_MUST_BE_LATER_MESSAGE,
    );
    expect(validateRenewalExpiryDate("17-06-20274", "18-07-2026")).toBe("Year must be exactly 4 digits.");
    expect(validateRenewalExpiryDate("32-13-2027", "18-07-2026")).toMatch(/valid calendar date|Invalid date format/);
    expect(validateRenewalExpiryDate("31-02-2027", "18-07-2026")).toBe("Please enter a valid calendar date.");
  });
});
