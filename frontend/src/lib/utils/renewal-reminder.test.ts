import { describe, expect, it } from "vitest";
import {
  buildRenewalReminderMessage,
  buildWhatsAppUri,
  getDefaultReminderChannel,
  hasPolicyEmail,
  RENEWAL_REMINDER_SUBJECT,
} from "./renewal-reminder";
import type { PolicyWithExtras } from "./policy-display";
import { LIC_PREMIUM_PAYMENT_URL } from "./premium-due-reminder";

const basePolicy: PolicyWithExtras = {
  id: 1,
  policy_number: "POL-2026-001",
  policyholder_name: "John",
  policy_type: "Health",
  expiry_date: "2026-06-15T00:00:00",
  preferred_channel: ["whatsapp"],
  status: "active",
  mobile_number: "9121529697",
};

describe("renewal-reminder", () => {
  it("builds the premium payment due reminder message", () => {
    const message = buildRenewalReminderMessage(basePolicy, "Uday Kumar");
    expect(message).toContain("Dear John,");
    expect(message).toContain("Premium due for Policy No. POL-2026-001 has not yet been received.");
    expect(message).toContain(LIC_PREMIUM_PAYMENT_URL);
    expect(message).toContain("Thank you,\nUday Kumar");
    expect(RENEWAL_REMINDER_SUBJECT).toBe("Premium Payment Reminder");
  });

  it("pre-selects whatsapp from preferred_channel", () => {
    expect(getDefaultReminderChannel(basePolicy)).toBe("whatsapp");
  });

  it("pre-selects email when preferred_channel is email", () => {
    const policy: PolicyWithExtras = {
      ...basePolicy,
      preferred_channel: ["email"],
      mobile_number: null,
      email: "john@example.com",
    };
    expect(getDefaultReminderChannel(policy)).toBe("email");
    expect(hasPolicyEmail(policy)).toBe(true);
  });

  it("builds a whatsapp uri with encoded message preserving newlines", () => {
    const body = "Line one\n\nLine two";
    const uri = buildWhatsAppUri("9121529697", body);
    expect(uri.startsWith("https://wa.me/919121529697?text=")).toBe(true);
    expect(decodeURIComponent(uri.split("text=")[1])).toBe(body);
  });
});
