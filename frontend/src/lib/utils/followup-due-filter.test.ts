import { describe, expect, it } from "vitest";
import {
  countFollowupsDueToday,
  countFollowupsDueWithinHours,
  countFollowupsMissed,
  countFollowupsOverdue,
  countFollowupsUpcoming,
  filterFollowupsByDue,
  followupDueDateKey,
  isFollowupDueToday,
  isFollowupDueWithinHours,
  isFollowupMissed,
  isFollowupOverdue,
  isFollowupUpcoming,
  todayUtcDateKey,
} from "./followup-due-filter";

describe("followup-due-filter", () => {
  const today = todayUtcDateKey();

  it("followupDueDateKey returns UTC YYYY-MM-DD", () => {
    expect(followupDueDateKey("2026-06-08T12:00:00.000Z")).toBe("2026-06-08");
  });

  it("isFollowupDueToday matches open leads due today", () => {
    expect(
      isFollowupDueToday({ status: "follow_up_pending", followup_due_at: `${today}T12:00:00.000Z` })
    ).toBe(true);
    expect(
      isFollowupDueToday({ status: "not_interested", followup_due_at: `${today}T12:00:00.000Z` })
    ).toBe(false);
  });

  it("isFollowupOverdue matches open leads before today", () => {
    expect(
      isFollowupOverdue({ status: "interested", followup_due_at: "2020-01-01T12:00:00.000Z" })
    ).toBe(true);
    expect(
      isFollowupOverdue({ status: "interested", followup_due_at: `${today}T12:00:00.000Z` })
    ).toBe(false);
  });

  it("filterFollowupsByDue applies today and overdue filters", () => {
    const records = [
      { id: 1, status: "follow_up_pending", followup_due_at: `${today}T12:00:00.000Z` },
      { id: 2, status: "interested", followup_due_at: "2020-01-01T12:00:00.000Z" },
      { id: 3, status: "renewed", followup_due_at: "2020-01-01T12:00:00.000Z" },
    ];
    expect(filterFollowupsByDue(records, "today")).toHaveLength(1);
    expect(filterFollowupsByDue(records, "overdue")).toHaveLength(1);
    expect(countFollowupsDueToday(records)).toBe(1);
    expect(countFollowupsOverdue(records)).toBe(1);
  });

  it("supports upcoming, 48h, and missed filters with date-based overdue logic", () => {
    const now = Date.now();
    const today = todayUtcDateKey();
    const records = [
      { id: 1, status: "follow_up_pending", followup_due_at: new Date(now + 6 * 60 * 60 * 1000).toISOString() },
      { id: 2, status: "interested", followup_due_at: new Date(now + 3 * 24 * 60 * 60 * 1000).toISOString() },
      { id: 3, status: "follow_up_later", followup_due_at: new Date(now - 24 * 60 * 60 * 1000).toISOString() },
      {
        id: 4,
        status: "follow_up_pending",
        followup_due_at: `${today}T09:00:00.000Z`,
      },
    ];

    expect(isFollowupUpcoming(records[0], now)).toBe(true);
    expect(isFollowupDueWithinHours(records[0], 48, now)).toBe(true);
    expect(isFollowupMissed(records[2], now)).toBe(true);
    expect(isFollowupMissed(records[3], now)).toBe(false);
    expect(isFollowupUpcoming(records[3], now)).toBe(true);
    expect(isFollowupDueWithinHours(records[3], 48, now)).toBe(true);
    expect(filterFollowupsByDue(records, "upcoming")).toHaveLength(3);
    expect(filterFollowupsByDue(records, "48h")).toHaveLength(2);
    expect(filterFollowupsByDue(records, "missed")).toHaveLength(1);
    expect(countFollowupsUpcoming(records)).toBe(3);
    expect(countFollowupsDueWithinHours(records, 48)).toBe(2);
    expect(countFollowupsMissed(records)).toBe(1);
  });
});
