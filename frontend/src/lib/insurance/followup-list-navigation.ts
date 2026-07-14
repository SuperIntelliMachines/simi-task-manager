import type { FollowupDueFilter } from "../utils/followup-due-filter";

export const FOLLOWUP_DUE_FILTER_LABELS: Record<FollowupDueFilter, string> = {
  today: "Due Today",
  overdue: "Overdue Follow-ups",
  upcoming: "Upcoming Follow-ups",
  "48h": "Due in Next 48 Hours",
  missed: "Missed Follow-ups",
};

export const FOLLOWUP_DUE_FILTER_DESCRIPTIONS: Partial<Record<FollowupDueFilter, string>> = {
  upcoming: "Open follow-ups scheduled from today onwards",
  "48h": "High-priority follow-ups due within the next 48 hours",
  missed: "Past-due follow-ups that still need agent attention",
};

export function followupListPath(due?: FollowupDueFilter | null): string {
  if (!due) return "/app/insurance/followups";
  return `/app/insurance/followups?due=${encodeURIComponent(due)}`;
}

export function parseFollowupDueFilter(value: string | null): FollowupDueFilter | null {
  if (
    value === "today" ||
    value === "overdue" ||
    value === "upcoming" ||
    value === "48h" ||
    value === "missed"
  ) {
    return value;
  }
  return null;
}
