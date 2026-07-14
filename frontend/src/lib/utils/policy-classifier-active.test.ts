import { describe, expect, it } from "vitest";

import {
  classifyDashboardKpis,
  isActivePolicy,
  isCriticalRenewal,
  isDue,
  isGracePeriod,
  isLapsed,
  isExpiring,
  isOtherActive,
} from "./policy-classifier";

function policy(expiry_date: string, status = "active") {
  return { expiry_date, status };
}

function futureDays(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

describe("classifyDashboardKpis", () => {
  it("matches business rules for overlapping renewal buckets", () => {
    const policies = [
      policy(futureDays(20)),
      policy(futureDays(8)),
      policy(futureDays(1)),
      policy(futureDays(-2)),
      policy(futureDays(-31)),
    ];

    const kpis = classifyDashboardKpis(policies);

    expect(kpis.total).toBe(5);
    expect(kpis.active).toBe(3);
    expect(kpis.due).toBe(1);
    expect(kpis.expiring).toBe(1);
    expect(kpis.grace_period).toBe(1);
    expect(kpis.lapsed).toBe(1);
  });

  it("keeps active as the union of renewal buckets and other active policies", () => {
    const policies = [
      policy(futureDays(45)),
      policy(futureDays(20)),
      policy(futureDays(5)),
      policy(futureDays(1)),
      policy(futureDays(-2)),
    ];

    const active = policies.filter(isActivePolicy);
    const bucketed =
      active.filter(isOtherActive).length +
      active.filter(isDue).length +
      active.filter(isCriticalRenewal).length;

    expect(active).toHaveLength(4);
    expect(bucketed).toBe(active.length);
    expect(classifyDashboardKpis(policies).active).toBe(4);
  });
});

describe("isActivePolicy", () => {
  it("includes active renewal buckets and other active policies", () => {
    expect(isActivePolicy(policy(futureDays(45)))).toBe(true);
    expect(isActivePolicy(policy(futureDays(20)))).toBe(true);
    expect(isActivePolicy(policy(futureDays(5)))).toBe(true);
    expect(isActivePolicy(policy(futureDays(1)))).toBe(true);
  });

  it("excludes grace period, lapsed, and cancelled policies", () => {
    expect(isActivePolicy(policy(futureDays(-2)))).toBe(false);
    expect(isActivePolicy(policy(futureDays(-31)))).toBe(false);
    expect(isActivePolicy(policy(futureDays(45), "cancelled"))).toBe(false);
    expect(isActivePolicy(policy(futureDays(5), "cancelled"))).toBe(false);
  });
});

describe("renewal windows", () => {
  it("classifies due renewals as 3-10 days and expiring as 0-2 days", () => {
    expect(isDue(policy(futureDays(10)))).toBe(true);
    expect(isDue(policy(futureDays(3)))).toBe(true);
    expect(isDue(policy(futureDays(11)))).toBe(false);
    expect(isDue(policy(futureDays(2)))).toBe(false);

    expect(isExpiring(policy(futureDays(2)))).toBe(true);
    expect(isExpiring(policy(futureDays(0)))).toBe(true);
    expect(isExpiring(policy(futureDays(3)))).toBe(false);
    expect(isGracePeriod(policy(futureDays(-2)))).toBe(true);
    expect(isLapsed(policy(futureDays(-31)))).toBe(true);
  });
});
