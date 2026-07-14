import { describe, expect, it } from "vitest";
import {
  getPolicyListStatusPriority,
  sortPoliciesByDefaultOrder,
} from "./policy-classifier";

function policy(
  id: number,
  expiry_date: string,
  status = "active",
) {
  return { id, expiry_date, status, policy_number: `POL-${id}`, policyholder_name: `Holder ${id}` };
}

describe("policy list default sort", () => {
  it("assigns status priority: expired=1, due=2, active=3", () => {
    expect(getPolicyListStatusPriority(policy(1, "2020-01-01"))).toBe(1);
    expect(getPolicyListStatusPriority(policy(2, futureDays(5)))).toBe(2);
    expect(getPolicyListStatusPriority(policy(3, futureDays(15)))).toBe(3);
    expect(getPolicyListStatusPriority(policy(4, futureDays(60)))).toBe(3);
  });

  it("sorts expired first, then due, then active", () => {
    const sorted = sortPoliciesByDefaultOrder([
      policy(4, futureDays(60)),
      policy(1, "2024-01-01"),
      policy(3, futureDays(8)),
      policy(2, "2025-01-01"),
      policy(5, futureDays(1)),
    ]);

    expect(sorted.map((p) => p.id)).toEqual([2, 1, 5, 3, 4]);
  });

  it("sorts by nearest expiry within each group", () => {
    const sorted = sortPoliciesByDefaultOrder([
      policy(1, "2023-01-01"),
      policy(2, "2024-06-01"),
      policy(3, futureDays(9)),
      policy(4, futureDays(4)),
      policy(5, futureDays(90)),
      policy(6, futureDays(120)),
    ]);

    expect(sorted.map((p) => p.id)).toEqual([2, 1, 4, 3, 5, 6]);
  });
});

function futureDays(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
