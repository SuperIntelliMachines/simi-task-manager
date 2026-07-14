import { describe, expect, it } from "vitest";

import { classifyPolicySummaryKpis } from "./policy-classifier";

function iso(daysFromNow: number) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + daysFromNow);
  return d.toISOString();
}

describe("classifyPolicySummaryKpis", () => {
  it("counts total, active, grace period, lapsed, and expiring soon", () => {
    const policies = [
      { status: "active", expiry_date: iso(20) },
      { status: "active", expiry_date: iso(5) },
      { status: "active", expiry_date: iso(1) },
      { status: "active", expiry_date: iso(-2) },
      { status: "active", expiry_date: iso(-31), grace_period_days: 30 },
      { status: "cancelled", expiry_date: iso(4) },
    ];

    expect(classifyPolicySummaryKpis(policies)).toEqual({
      total_policies: 6,
      active_policies: 3,
      grace_period_policies: 1,
      lapsed_policies: 1,
      expiring_soon_policies: 2,
    });
  });
});
