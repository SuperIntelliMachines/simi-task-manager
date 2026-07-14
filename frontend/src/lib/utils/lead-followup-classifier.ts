import {
  countFollowupsDueWithinHours,
  countFollowupsMissed,
  countFollowupsUpcoming,
  type FollowupRecord,
} from "./followup-due-filter";

export type LeadFollowupOverview = {
  total_leads: number;
  upcoming_followups: number;
  due_in_48_hours: number;
  missed_followups: number;
};

/** KPI counts for Lead Follow-up Overview (mirrors backend classify_lead_followup_overview). */
export function classifyLeadFollowupOverview(leads: FollowupRecord[]): LeadFollowupOverview {
  return {
    total_leads: leads.length,
    upcoming_followups: countFollowupsUpcoming(leads),
    due_in_48_hours: countFollowupsDueWithinHours(leads, 48),
    missed_followups: countFollowupsMissed(leads),
  };
}
