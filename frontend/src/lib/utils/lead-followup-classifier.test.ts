import { describe, expect, it } from "vitest";
import { classifyLeadFollowupOverview } from "./lead-followup-classifier";

describe("classifyLeadFollowupOverview", () => {
  it("mirrors backend lead follow-up KPI counts", () => {
    const now = Date.now();
    const leads = [
      { status: "follow_up_pending", followup_due_at: new Date(now + 6 * 60 * 60 * 1000).toISOString() },
      { status: "interested", followup_due_at: new Date(now + 3 * 24 * 60 * 60 * 1000).toISOString() },
      { status: "follow_up_later", followup_due_at: new Date(now - 24 * 60 * 60 * 1000).toISOString() },
      { status: "renewed", followup_due_at: new Date(now - 24 * 60 * 60 * 1000).toISOString() },
      { status: "open", followup_due_at: null },
      { status: "follow_up_pending", followup_due_at: new Date(now + 30 * 60 * 60 * 1000).toISOString() },
    ];

    expect(classifyLeadFollowupOverview(leads)).toEqual({
      total_leads: 6,
      upcoming_followups: 3,
      due_in_48_hours: 2,
      missed_followups: 1,
    });
  });
});
