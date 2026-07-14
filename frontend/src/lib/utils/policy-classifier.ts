// Reusable policy classification utilities
export type PolicyCategory = "lapsed" | "grace_period" | "expiring" | "due" | "other" | "unknown";

export const DUE_RENEWAL_MIN_DAYS = 3;
export const DUE_RENEWAL_MAX_DAYS = 10;
export const EXPIRING_MIN_DAYS = 0;
export const EXPIRING_MAX_DAYS = 2;
export const POLICY_SUMMARY_EXPIRING_SOON_MAX_DAYS = 10;
export const DEFAULT_GRACE_PERIOD_DAYS = 30;

const INACTIVE_TRACKING_STATUSES = new Set(["cancelled"]);

function parseDateOnlyToUTC(dateStr: string | null | undefined): Date | null {
  if (!dateStr) return null;
  const ddmm = /^\s*(\d{2})-(\d{2})-(\d{4})\s*$/.exec(dateStr);
  if (ddmm) {
    const day = Number(ddmm[1]);
    const month = Number(ddmm[2]) - 1;
    const year = Number(ddmm[3]);
    return new Date(Date.UTC(year, month, day));
  }
  const ymd = /^\s*(\d{4})-(\d{2})-(\d{2})/.exec(dateStr);
  if (ymd) {
    const year = Number(ymd[1]);
    const month = Number(ymd[2]) - 1;
    const day = Number(ymd[3]);
    return new Date(Date.UTC(year, month, day));
  }
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
}

export function daysUntilUTC(dateIso: string | null | undefined): number {
  const target = parseDateOnlyToUTC(dateIso as string);
  if (!target) return NaN;
  const now = new Date();
  const utcStart = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const utcTarget = Date.UTC(target.getUTCFullYear(), target.getUTCMonth(), target.getUTCDate());
  const diff = (utcTarget - utcStart) / (1000 * 60 * 60 * 24);
  return Math.round(diff);
}

export function classifyByDays(days: number): PolicyCategory {
  if (Number.isNaN(days)) return "unknown";
  if (days < 0) return "grace_period";
  if (days >= EXPIRING_MIN_DAYS && days <= EXPIRING_MAX_DAYS) return "expiring";
  if (days >= DUE_RENEWAL_MIN_DAYS && days <= DUE_RENEWAL_MAX_DAYS) return "due";
  return "other";
}

export function evaluatePolicyStatus(policy: any): "active" | "grace_period" | "lapsed" | "renewed" | "escalated" {
  const status = String(policy?.status ?? "").toLowerCase();
  if (status === "renewed" || status === "escalated") return status;

  const days = daysUntilUTC(policy?.expiry_date);
  if (Number.isNaN(days)) return "active";
  if (days >= 0) return "active";

  const graceDays = Math.max(Number(policy?.grace_period_days ?? DEFAULT_GRACE_PERIOD_DAYS), 0);
  const overdueDays = Math.abs(days);
  return overdueDays <= graceDays ? "grace_period" : "lapsed";
}

export function classifyPolicy(policy: any): { category: PolicyCategory; daysRemaining: number } {
  const days = daysUntilUTC(policy?.expiry_date);
  const lifecycle = evaluatePolicyStatus(policy);
  const category =
    lifecycle === "lapsed"
      ? "lapsed"
      : lifecycle === "grace_period"
        ? "grace_period"
        : classifyByDays(days);
  return { category, daysRemaining: days };
}

export function isGracePeriod(policy: any) {
  return evaluatePolicyStatus(policy) === "grace_period";
}

export function isLapsed(policy: any) {
  return evaluatePolicyStatus(policy) === "lapsed";
}

/** Active lifecycle bucket (on/before renewal date), excluding cancelled. */
export function isActivePolicy(policy: any) {
  if (!policy) return false;
  const status = String(policy?.status ?? "").toLowerCase();
  if (INACTIVE_TRACKING_STATUSES.has(status)) return false;
  return evaluatePolicyStatus(policy) === "active";
}

/** Expiring policies: 0–2 days remaining (active policies only). */
export function isExpiring(policy: any, maxDays = EXPIRING_MAX_DAYS) {
  if (!isActivePolicy(policy)) return false;
  const days = daysUntilUTC(policy?.expiry_date);
  return !Number.isNaN(days) && EXPIRING_MIN_DAYS <= days && days <= (maxDays ?? EXPIRING_MAX_DAYS);
}

export function isCriticalRenewal(policy: any) {
  return isExpiring(policy, EXPIRING_MAX_DAYS);
}

/** Due renewals: 3–10 days remaining (active policies only). */
export function isDue(policy: any) {
  if (!isActivePolicy(policy)) return false;
  const days = daysUntilUTC(policy?.expiry_date);
  return !Number.isNaN(days) && days >= DUE_RENEWAL_MIN_DAYS && days <= DUE_RENEWAL_MAX_DAYS;
}

/** Backward-compatible alias for due renewals. */
export function isUpcomingRenewal(policy: any) {
  return isDue(policy);
}

export function isOtherActive(policy: any) {
  if (!policy) return false;
  return isActivePolicy(policy) && !isDue(policy) && !isExpiring(policy);
}

export function getPolicyListStatusPriority(policy: any): number {
  if (isLapsed(policy)) return 1;
  if (isGracePeriod(policy)) return 2;
  if (isCriticalRenewal(policy) || isDue(policy)) return 2;
  return 3;
}

export function sortPoliciesByDefaultOrder<T extends { expiry_date: string; status?: string | null }>(
  policies: T[],
): T[] {
  return [...policies].sort((a, b) => {
    const priorityDiff = getPolicyListStatusPriority(a) - getPolicyListStatusPriority(b);
    if (priorityDiff !== 0) return priorityDiff;

    const expiryA = new Date(a.expiry_date).getTime();
    const expiryB = new Date(b.expiry_date).getTime();
    if (Number.isNaN(expiryA) || Number.isNaN(expiryB)) {
      return String(a.expiry_date || "").localeCompare(String(b.expiry_date || ""));
    }

    if (getPolicyListStatusPriority(a) === 1) {
      return expiryB - expiryA;
    }
    return expiryA - expiryB;
  });
}

export type RenewalCategory = "critical" | "due_soon" | "upcoming";

/** Policies in the due or expiring renewal windows (0–10 days, active only). */
export function isWithinRenewalWindow(policy: any) {
  return isDue(policy) || isExpiring(policy);
}

export function getRenewalCategory(policy: any): RenewalCategory | null {
  if (!isActivePolicy(policy)) return null;
  if (isCriticalRenewal(policy)) return "critical";
  if (isDue(policy)) return "due_soon";
  return null;
}

export function sortByNearestExpiry<T extends { expiry_date: string }>(policies: T[]): T[] {
  return [...policies].sort(
    (a, b) => new Date(a.expiry_date).getTime() - new Date(b.expiry_date).getTime(),
  );
}

export function categorizeRenewals<T extends { expiry_date: string; status?: string | null }>(policies: T[]) {
  const inWindow = sortByNearestExpiry(policies.filter(isWithinRenewalWindow));
  return {
    critical: inWindow.filter((p) => isCriticalRenewal(p)),
    dueSoon: inWindow.filter((p) => isDue(p)),
    all: inWindow,
  };
}

export type DashboardKpis = {
  total: number;
  active: number;
  due: number;
  expiring: number;
  grace_period: number;
  lapsed: number;
};

export type PolicySummaryKpis = {
  total_policies: number;
  active_policies: number;
  grace_period_policies: number;
  lapsed_policies: number;
  expiring_soon_policies: number;
};

export function hasActiveStatus(policy: any) {
  return evaluatePolicyStatus(policy) === "active";
}

/** Active-status policies expiring within the next N days (Policy Summary KPI). */
export function isExpiringSoonPolicy(policy: any, maxDays = POLICY_SUMMARY_EXPIRING_SOON_MAX_DAYS) {
  if (!hasActiveStatus(policy)) return false;
  const days = daysUntilUTC(policy?.expiry_date);
  return !Number.isNaN(days) && EXPIRING_MIN_DAYS <= days && days <= maxDays;
}

/** KPI counts for the Policy Summary section (mirrors backend classify_policy_summary_kpis). */
export function classifyPolicySummaryKpis(policies: any[]): PolicySummaryKpis {
  return {
    total_policies: policies.length,
    active_policies: policies.filter((p) => hasActiveStatus(p) && !isLapsed(p)).length,
    grace_period_policies: policies.filter(isGracePeriod).length,
    lapsed_policies: policies.filter(isLapsed).length,
    expiring_soon_policies: policies.filter((p) => isExpiringSoonPolicy(p)).length,
  };
}

/** Single source of truth for Insurance dashboard KPI cards. */
export function classifyDashboardKpis(policies: any[]): DashboardKpis {
  return {
    total: policies.length,
    active: policies.filter(isActivePolicy).length,
    due: policies.filter(isDue).length,
    expiring: policies.filter((p) => isExpiring(p)).length,
    grace_period: policies.filter(isGracePeriod).length,
    lapsed: policies.filter(isLapsed).length,
  };
}

export default {
  daysUntilUTC,
  classifyPolicy,
  classifyDashboardKpis,
  isExpiring,
  isDue,
  isGracePeriod,
  isLapsed,
  isActivePolicy,
  isOtherActive,
  isWithinRenewalWindow,
  isUpcomingRenewal,
  getRenewalCategory,
  sortByNearestExpiry,
  categorizeRenewals,
  getPolicyListStatusPriority,
  sortPoliciesByDefaultOrder,
};
