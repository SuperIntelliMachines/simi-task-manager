import { describe, expect, it } from "vitest";
import { buildRenewalSmsMessage, buildSmsUri, hasPolicyMobile } from "./renewal-sms";
import type { PolicyWithExtras } from "./policy-display";
import { LIC_PREMIUM_PAYMENT_URL } from "./premium-due-reminder";

const samplePolicy: PolicyWithExtras = {
  id: 1,
  policy_number: "POL-2026-441",
  policyholder_name: "Ravi Sharma",
  policy_type: "Auto",
  expiry_date: "2026-06-15T00:00:00",
  preferred_channel: ["whatsapp"],
  status: "active",
  mobile: "+91 98765 43210",
};

describe("renewal-sms", () => {
  it("builds the premium payment due SMS template", () => {
    const message = buildRenewalSmsMessage(samplePolicy, "Uday Kumar");
    expect(message).toContain("Dear Ravi Sharma,");
    expect(message).toContain("Premium due for Policy No. POL-2026-441 has not yet been received.");
    expect(message).toContain(LIC_PREMIUM_PAYMENT_URL);
    expect(message).toContain("Thank you,\nUday Kumar");
  });

  it("builds an sms uri with encoded body", () => {
    const uri = buildSmsUri("+91 98765 43210", "Hello there");
    expect(uri.startsWith("sms:+919876543210?body=")).toBe(true);
    expect(decodeURIComponent(uri.split("body=")[1])).toBe("Hello there");
  });

  it("detects when a policy has a mobile number", () => {
    expect(hasPolicyMobile({ ...samplePolicy, mobile_number: "9121529697" })).toBe(true);
    expect(hasPolicyMobile(samplePolicy)).toBe(true);
    expect(hasPolicyMobile({ ...samplePolicy, mobile_number: null, mobile: null })).toBe(false);
  });
});
