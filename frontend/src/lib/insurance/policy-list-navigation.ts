export type PolicyListFilter = "active" | "due" | "expiring" | "expiring_soon" | "grace_period" | "lapsed" | "expired";

export const POLICY_LIST_FILTER_LABELS: Record<PolicyListFilter | "all", string> = {
  all: "All Policies",
  active: "Active Policies",
  due: "Due Renewals",
  expiring: "Expiring Policies",
  expiring_soon: "Renewal Due Soon (0–10 Days)",
  grace_period: "Grace Period",
  lapsed: "Lapsed Policies",
  expired: "Expired Policies",
};

export const POLICY_LIST_FILTER_DESCRIPTIONS: Partial<Record<PolicyListFilter, string>> = {
  active: "Policies within renewal date (including due/expiring windows)",
  due: "Policies expiring in 3–10 days",
  expiring: "Policies expiring in 0–2 days",
  expiring_soon: "Active policies expiring within the next 10 days",
  grace_period: "Policies within grace window after renewal date",
  lapsed: "Policies beyond grace window and not renewed",
};

export function policyListPath(filter?: PolicyListFilter | null): string {
  if (!filter) return "/app/insurance/policies";
  return `/app/insurance/policies?filter=${filter}`;
}

export function parsePolicyListFilter(value: string | null): PolicyListFilter | null {
  if (
    value === "active" ||
    value === "due" ||
    value === "expiring" ||
    value === "expiring_soon" ||
    value === "grace_period" ||
    value === "lapsed" ||
    value === "expired"
  ) {
    return value;
  }
  return null;
}
