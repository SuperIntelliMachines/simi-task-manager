import { describe, expect, it } from "vitest";
import { buildPremiumPaymentDueMessage, LIC_PREMIUM_PAYMENT_URL } from "./premium-due-reminder";

describe("premium-due-reminder", () => {
  it("builds the premium payment due message with line breaks", () => {
    const message = buildPremiumPaymentDueMessage({
      customerName: "John",
      policyNumber: "POL-2026-001",
      loggedInUserName: "Uday Kumar",
    });

    expect(message).toBe(
      `Dear John,

Premium due for Policy No. POL-2026-001 has not yet been received.

Please pay your premium online:
${LIC_PREMIUM_PAYMENT_URL}

Kindly ignore this message if payment has already been made.

Thank you,
Uday Kumar`,
    );
  });
});
