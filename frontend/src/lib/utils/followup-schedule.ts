/** Compute follow-up due date as ISO string from today + N days. */
export function followupDueAtFromDays(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + days);
  d.setUTCHours(12, 0, 0, 0);
  return d.toISOString();
}

/** Parse YYYY-MM-DD from <input type="date"> to ISO string. */
export function followupDueAtFromDateInput(dateStr: string): string | null {
  if (!dateStr) return null;
  const parts = dateStr.split("-");
  if (parts.length !== 3) return null;
  const y = Number(parts[0]);
  const m = Number(parts[1]) - 1;
  const day = Number(parts[2]);
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(day)) return null;
  return new Date(Date.UTC(y, m, day, 12, 0, 0)).toISOString();
}

export type LeadFollowupActionStatus = "interested" | "not_interested" | "follow_up_later";

export const LEAD_FOLLOWUP_ACTION_OPTIONS: Array<{ value: LeadFollowupActionStatus; label: string }> = [
  { value: "interested", label: "Interested" },
  { value: "not_interested", label: "Not Interested" },
  { value: "follow_up_later", label: "Follow Up Later" },
];

export const LEAD_STATUS_LABELS: Record<string, string> = {
  follow_up_pending: "Pending",
  open: "Open",
  interested: "Interested",
  renewed: "Renewed",
  not_interested: "Not Interested",
  follow_up_later: "Follow-up Later",
};

export const LEAD_STATUS_TOAST: Record<string, string> = {
  interested: "Status updated to Interested.",
  not_interested: "Lead marked as not interested.",
  follow_up_later: "Follow-up rescheduled successfully.",
};

export function leadStatusLabel(status: string | null | undefined): string {
  if (!status) return "Unknown";
  return LEAD_STATUS_LABELS[status] ?? status;
}
