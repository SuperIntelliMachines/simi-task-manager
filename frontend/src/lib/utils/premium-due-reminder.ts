export const LIC_PREMIUM_PAYMENT_URL = "https://ebiz.licindia.in/spy-LIC";

export const PREMIUM_PAYMENT_DUE_TEMPLATE = `Dear {customerName},

Premium due for Policy No. {policyNumber} has not yet been received.

Please pay your premium online:
${LIC_PREMIUM_PAYMENT_URL}

Kindly ignore this message if payment has already been made.

Thank you,
{loggedInUserName}`;

export type PremiumPaymentDueParams = {
  customerName: string;
  policyNumber: string;
  loggedInUserName: string;
};

export function buildPremiumPaymentDueMessage({
  customerName,
  policyNumber,
  loggedInUserName,
}: PremiumPaymentDueParams): string {
  return PREMIUM_PAYMENT_DUE_TEMPLATE.replace("{customerName}", customerName || "Customer")
    .replace("{policyNumber}", policyNumber || "-")
    .replace("{loggedInUserName}", loggedInUserName || "SIMI Insurance");
}
