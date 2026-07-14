import { describe, expect, it } from "vitest";
import {
  followupDueAtFromDateInput,
  followupDueAtFromDays,
  leadStatusLabel,
  LEAD_FOLLOWUP_ACTION_OPTIONS,
  LEAD_STATUS_TOAST,
} from "./followup-schedule";

describe("followup-schedule", () => {
  it("followupDueAtFromDays adds days from today", () => {
    const iso = followupDueAtFromDays(5);
    const d = new Date(iso);
    const now = new Date();
    const expected = new Date(now);
    expected.setUTCDate(expected.getUTCDate() + 5);
    expect(d.getUTCFullYear()).toBe(expected.getUTCFullYear());
    expect(d.getUTCMonth()).toBe(expected.getUTCMonth());
    expect(d.getUTCDate()).toBe(expected.getUTCDate());
  });

  it("followupDueAtFromDateInput parses YYYY-MM-DD", () => {
    const iso = followupDueAtFromDateInput("2026-12-25");
    expect(iso).toBeTruthy();
    expect(iso!.startsWith("2026-12-25")).toBe(true);
  });

  it("leadStatusLabel maps known statuses", () => {
    expect(leadStatusLabel("interested")).toBe("Interested");
    expect(leadStatusLabel("follow_up_later")).toBe("Follow-up Later");
  });

  it("LEAD_STATUS_TOAST includes follow_up_later confirmation", () => {
    expect(LEAD_STATUS_TOAST.follow_up_later).toBe("Follow-up rescheduled successfully.");
  });

  it("LEAD_FOLLOWUP_ACTION_OPTIONS excludes renewed", () => {
    expect(LEAD_FOLLOWUP_ACTION_OPTIONS.map((option) => option.value)).toEqual([
      "interested",
      "not_interested",
      "follow_up_later",
    ]);
    expect(LEAD_FOLLOWUP_ACTION_OPTIONS.some((option) => (option.value as string) === "renewed")).toBe(false);
  });
});
