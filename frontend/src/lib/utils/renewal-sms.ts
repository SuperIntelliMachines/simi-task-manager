import type { PolicyRenewalSmsResponse } from "../api/types";
import { apiClient } from "../api/client";
import type { PolicyWithExtras } from "./policy-display";
import { getPolicyMobileValue, hasPolicyMobileNumber } from "./policy-display";
import { buildPremiumPaymentDueMessage, LIC_PREMIUM_PAYMENT_URL } from "./premium-due-reminder";

export function buildRenewalSmsMessage(policy: PolicyWithExtras, loggedInUserName: string): string {
  return buildPremiumPaymentDueMessage({
    customerName: policy.policyholder_name || "Customer",
    policyNumber: policy.policy_number || "-",
    loggedInUserName,
  });
}

export function normalizeMobileForSms(mobile: string): string {
  return mobile.replace(/\s/g, "");
}

export function buildSmsUri(mobile: string, message: string): string {
  const normalized = normalizeMobileForSms(mobile).replace(/[^\d+]/g, "");
  return `sms:${normalized}?body=${encodeURIComponent(message)}`;
}

export function hasPolicyMobile(policy: PolicyWithExtras): boolean {
  return hasPolicyMobileNumber(policy);
}

export async function openRenewalSmsWorkflow(
  policy: PolicyWithExtras,
  options: { loggedInUserName: string; actorUserId?: number | null },
): Promise<PolicyRenewalSmsResponse> {
  const mobileValue = getPolicyMobileValue(policy);
  if (!mobileValue) {
    throw new Error("No mobile number on file");
  }

  try {
    const result = await apiClient.sendPolicyRenewalSms(policy.id, {
      actorUserId: options.actorUserId,
      loggedInUserName: options.loggedInUserName,
    });
    if (result.mode === "client" && result.sms_uri) {
      window.open(result.sms_uri, "_self");
    }
    return result;
  } catch {
    const message = buildRenewalSmsMessage(policy, options.loggedInUserName);
    const smsUri = buildSmsUri(mobileValue, message);
    window.open(smsUri, "_self");
    return {
      mode: "client",
      mobile: mobileValue,
      policyholder_name: policy.policyholder_name,
      policy_number: policy.policy_number,
      payment_link: LIC_PREMIUM_PAYMENT_URL,
      logged_in_user_name: options.loggedInUserName,
      message,
      sms_uri: smsUri,
    };
  }
}
