import type { InsurancePolicyCard } from "../api/types";
import { classifyPolicy, daysUntilUTC, isExpiringSoonPolicy } from "./policy-classifier";

export type PolicyWithExtras = InsurancePolicyCard & {
  premium?: number | string | null;
  currency?: string | null;
  policy_metadata?: Record<string, unknown> | null;
};

export const EMPTY_MOBILE_DISPLAY = "-";

function readTrimmed(value: unknown): string | null {
  if (value == null) return null;
  const trimmed = String(value).trim();
  return trimmed || null;
}

export function getPolicyMobileValue(policy: PolicyWithExtras): string | null {
  const meta = policy.policy_metadata ?? {};
  return (
    readTrimmed(policy.mobile_number) ||
    readTrimmed(policy.mobile) ||
    readTrimmed(policy.contact_phone) ||
    readTrimmed(meta.mobile) ||
    readTrimmed(meta.phone) ||
    readTrimmed(meta.contact_phone)
  );
}

export function getPolicyMobile(policy: PolicyWithExtras): string {
  return getPolicyMobileValue(policy) ?? EMPTY_MOBILE_DISPLAY;
}

export function getPolicyEmailValue(policy: PolicyWithExtras): string | null {
  return readTrimmed(policy.email) || readTrimmed(policy.contact_email);
}

export function getPolicyEmail(policy: PolicyWithExtras): string {
  return getPolicyEmailValue(policy) ?? EMPTY_MOBILE_DISPLAY;
}

export function hasPolicyMobileNumber(policy: PolicyWithExtras): boolean {
  return getPolicyMobileValue(policy) != null;
}

export function formatPolicyPremium(policy: PolicyWithExtras): string {
  if (policy.premium == null || policy.premium === "") return "—";
  const amount = Number(policy.premium);
  if (Number.isNaN(amount)) return "—";
  const currency = policy.currency || "INR";
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
}

export function formatDaysRemaining(policy: PolicyWithExtras): string {
  const days = daysUntilUTC(policy.expiry_date);
  if (Number.isNaN(days)) return "—";
  if (days === 0) return "Today";
  if (days === 1) return "1 day";
  return `${days} days`;
}

export type PolicyStatusBadgeDisplay = {
  label: string;
  className: string;
};

export function getPolicyListStatusBadge(policy: PolicyWithExtras): PolicyStatusBadgeDisplay {
  const { category } = classifyPolicy(policy);

  if (category === "lapsed") {
    return {
      label: "Lapsed",
      className: "bg-red-100 text-red-700 border border-red-200 dark:bg-red-500/15 dark:text-red-300 dark:border-red-500/25",
    };
  }

  if (category === "grace_period") {
    return {
      label: "Grace Period",
      className: "bg-amber-100 text-amber-700 border border-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/25",
    };
  }

  if (isExpiringSoonPolicy(policy) || category === "expiring" || category === "due") {
    return {
      label: "Renewal Due Soon",
      className: "bg-orange-100 text-orange-700 border border-orange-200 dark:bg-orange-500/15 dark:text-orange-300 dark:border-orange-500/25",
    };
  }

  return {
    label: "Active",
    className: "bg-green-100 text-green-700 border border-green-200 dark:bg-[#14B8A6]/15 dark:text-[#14B8A6] dark:border-[#14B8A6]/25",
  };
}
