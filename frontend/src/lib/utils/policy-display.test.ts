import { describe, expect, it } from "vitest";
import {
  EMPTY_MOBILE_DISPLAY,
  getPolicyEmail,
  getPolicyEmailValue,
  getPolicyListStatusBadge,
  getPolicyMobile,
  getPolicyMobileValue,
  hasPolicyMobileNumber,
  type PolicyWithExtras,
} from "./policy-display";

const basePolicy: PolicyWithExtras = {
  id: 1,
  policy_number: "POL-2026-001",
  policyholder_name: "John",
  policy_type: "Health",
  expiry_date: "2026-06-15T00:00:00",
      preferred_channel: ["whatsapp"],
  status: "active",
};

describe("policy-display mobile helpers", () => {
  it("prefers mobile_number over legacy mobile fields", () => {
    const policy: PolicyWithExtras = {
      ...basePolicy,
      mobile_number: "9121529697",
      mobile: "+91 98765 43210",
    };

    expect(getPolicyMobileValue(policy)).toBe("9121529697");
    expect(getPolicyMobile(policy)).toBe("9121529697");
    expect(hasPolicyMobileNumber(policy)).toBe(true);
  });

  it("falls back to contact mobile fields when mobile_number is missing", () => {
    const policy: PolicyWithExtras = {
      ...basePolicy,
      mobile: "+91 98765 43210",
    };

    expect(getPolicyMobile(policy)).toBe("+91 98765 43210");
  });

  it("returns dash display when no mobile is available", () => {
    expect(getPolicyMobile(basePolicy)).toBe(EMPTY_MOBILE_DISPLAY);
    expect(getPolicyMobileValue(basePolicy)).toBeNull();
    expect(hasPolicyMobileNumber(basePolicy)).toBe(false);
  });
});

describe("policy-display status badge", () => {
  it("maps expired policies to Pending Renewal", () => {
    const badge = getPolicyListStatusBadge({
      ...basePolicy,
      expiry_date: "2020-01-01T00:00:00",
      status: "active",
    });
    expect(badge.label).toBe("Pending Renewal");
  });

  it("maps expiring soon policies to Renewal Due Soon", () => {
    const future = new Date();
    future.setUTCDate(future.getUTCDate() + 5);
    const badge = getPolicyListStatusBadge({
      ...basePolicy,
      expiry_date: future.toISOString(),
      status: "active",
    });
    expect(badge.label).toBe("Renewal Due Soon");
  });

  it("maps healthy policies to Active", () => {
    const future = new Date();
    future.setUTCDate(future.getUTCDate() + 60);
    const badge = getPolicyListStatusBadge({
      ...basePolicy,
      expiry_date: future.toISOString(),
      status: "active",
    });
    expect(badge.label).toBe("Active");
  });
});

describe("policy-display email helpers", () => {
  it("prefers email over contact_email", () => {
    const policy: PolicyWithExtras = {
      ...basePolicy,
      email: "kanithiudaykumar324@gmail.com",
      contact_email: "other@example.com",
    };

    expect(getPolicyEmailValue(policy)).toBe("kanithiudaykumar324@gmail.com");
    expect(getPolicyEmail(policy)).toBe("kanithiudaykumar324@gmail.com");
  });

  it("falls back to contact_email when email is missing", () => {
    const policy: PolicyWithExtras = {
      ...basePolicy,
      contact_email: "holder@example.com",
    };

    expect(getPolicyEmail(policy)).toBe("holder@example.com");
  });

  it("returns dash display when no email is available", () => {
    expect(getPolicyEmail(basePolicy)).toBe("-");
    expect(getPolicyEmail({ ...basePolicy, email: "   " })).toBe("-");
    expect(getPolicyEmailValue(basePolicy)).toBeNull();
  });
});
