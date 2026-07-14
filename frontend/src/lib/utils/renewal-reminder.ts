import type { PolicyWithExtras } from "./policy-display";
import { getPolicyMobileValue, hasPolicyMobileNumber } from "./policy-display";
import { apiClient } from "../api/client";
import { buildPremiumPaymentDueMessage } from "./premium-due-reminder";

export type ReminderChannel = "whatsapp" | "sms" | "email";

export const RENEWAL_REMINDER_SUBJECT = "Premium Payment Reminder";

export const SMS_INTEGRATION_UNAVAILABLE = "SMS integration coming soon.";

export function getPolicyEmailValue(policy: PolicyWithExtras): string | null {
  const meta = policy.policy_metadata ?? {};
  const value =
    policy.email?.trim() ||
    policy.contact_email?.trim() ||
    (typeof meta.email === "string" ? meta.email.trim() : "") ||
    (typeof meta.contact_email === "string" ? meta.contact_email.trim() : "");
  return value || null;
}

export function hasPolicyEmail(policy: PolicyWithExtras): boolean {
  return getPolicyEmailValue(policy) != null;
}

export function buildRenewalReminderMessage(
  policy: PolicyWithExtras,
  loggedInUserName: string,
): string {
  return buildPremiumPaymentDueMessage({
    customerName: policy.policyholder_name || "Customer",
    policyNumber: policy.policy_number || "-",
    loggedInUserName,
  });
}

export function getDefaultReminderChannel(policy: PolicyWithExtras): ReminderChannel {
  const channels = Array.isArray(policy.preferred_channel)
    ? policy.preferred_channel.map((channel) => channel.toLowerCase())
    : [];
  const preferred = channels[0] || "";

  if (preferred === "whatsapp" && hasPolicyMobileNumber(policy)) {
    return "whatsapp";
  }
  if (preferred === "email" && hasPolicyEmail(policy)) {
    return "email";
  }
  if ((preferred === "sms" || preferred === "telegram") && hasPolicyMobileNumber(policy)) {
    return "sms";
  }
  if (hasPolicyMobileNumber(policy)) {
    return "whatsapp";
  }
  if (hasPolicyEmail(policy)) {
    return "email";
  }
  return "sms";
}

function normalizeWhatsAppPhone(mobile: string): string {
  const digits = mobile.replace(/\D/g, "");
  if (digits.length === 10) {
    return `91${digits}`;
  }
  return digits;
}

export function buildWhatsAppUri(mobile: string, message: string): string {
  const phone = normalizeWhatsAppPhone(mobile);
  return `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
}

export function openWhatsAppReminder(policy: PolicyWithExtras, loggedInUserName: string): void {
  const mobile = getPolicyMobileValue(policy);
  if (!mobile) return;
  window.open(buildWhatsAppUri(mobile, buildRenewalReminderMessage(policy, loggedInUserName)), "_blank");
}

export function buildMailtoUri(email: string, subject: string, body: string): string {
  return `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export function openEmailReminder(policy: PolicyWithExtras, loggedInUserName: string): void {
  const email = getPolicyEmailValue(policy);
  if (!email) return;
  const uri = buildMailtoUri(
    email,
    RENEWAL_REMINDER_SUBJECT,
    buildRenewalReminderMessage(policy, loggedInUserName),
  );
  window.open(uri, "_self");
}

export async function sendSmsReminder(
  policy: PolicyWithExtras,
  options: { loggedInUserName: string; actorUserId?: number | null },
): Promise<{ sent: boolean; message?: string }> {
  if (!hasPolicyMobileNumber(policy)) {
    return { sent: false, message: SMS_INTEGRATION_UNAVAILABLE };
  }

  try {
    const result = await apiClient.sendPolicyRenewalSms(policy.id, {
      actorUserId: options.actorUserId,
      loggedInUserName: options.loggedInUserName,
    });
    if (result.mode === "sent") {
      return { sent: true };
    }
    return { sent: false, message: SMS_INTEGRATION_UNAVAILABLE };
  } catch {
    return { sent: false, message: SMS_INTEGRATION_UNAVAILABLE };
  }
}
