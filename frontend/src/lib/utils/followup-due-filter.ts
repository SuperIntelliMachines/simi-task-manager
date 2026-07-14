/** Open lead statuses — must stay aligned with backend OPEN_LEAD_STATUSES. */
export const OPEN_LEAD_STATUSES = new Set([
  "open",
  "follow_up_pending",
  "follow_up_later",
  "interested",
]);

export type FollowupDueFilter = "today" | "overdue" | "upcoming" | "48h" | "missed";

type FollowupRecord = {
  status?: string;
  followup_due_at?: string | null;
};

export type { FollowupRecord };

function followupDueTimestamp(isoStr: string | null | undefined): number | null {
  if (!isoStr) return null;
  const ts = new Date(isoStr).getTime();
  return Number.isNaN(ts) ? null : ts;
}

/** UTC date key YYYY-MM-DD for consistent due-date comparisons. */
export function followupDueDateKey(isoStr: string | null | undefined): string | null {
  if (!isoStr) return null;
  const d = new Date(isoStr);
  if (Number.isNaN(d.getTime())) return null;
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function todayUtcDateKey(): string {
  const d = new Date();
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function isOpenLeadStatus(status: string | null | undefined): boolean {
  return status != null && OPEN_LEAD_STATUSES.has(status);
}

export function isFollowupDueToday(record: FollowupRecord): boolean {
  if (!isOpenLeadStatus(record.status)) return false;
  const dueKey = followupDueDateKey(record.followup_due_at);
  return dueKey != null && dueKey === todayUtcDateKey();
}

export function isFollowupOverdue(record: FollowupRecord): boolean {
  if (!isOpenLeadStatus(record.status)) return false;
  const dueKey = followupDueDateKey(record.followup_due_at);
  const today = todayUtcDateKey();
  return dueKey != null && dueKey < today;
}

export function isFollowupUpcoming(record: FollowupRecord, nowMs: number = Date.now()): boolean {
  if (!isOpenLeadStatus(record.status)) return false;
  const dueKey = followupDueDateKey(record.followup_due_at);
  return dueKey != null && dueKey >= todayUtcDateKey();
}

export function isFollowupDueWithinHours(
  record: FollowupRecord,
  hours: number = 48,
  nowMs: number = Date.now()
): boolean {
  if (!isOpenLeadStatus(record.status)) return false;
  const dueTs = followupDueTimestamp(record.followup_due_at);
  if (dueTs == null) return false;
  const dueKey = followupDueDateKey(record.followup_due_at);
  if (dueKey === todayUtcDateKey()) return true;
  const windowEnd = nowMs + hours * 60 * 60 * 1000;
  return dueTs >= nowMs && dueTs <= windowEnd;
}

export function isFollowupMissed(record: FollowupRecord, _nowMs: number = Date.now()): boolean {
  return isFollowupOverdue(record);
}

export function filterFollowupsByDue(
  records: FollowupRecord[],
  due: FollowupDueFilter | null | undefined
): FollowupRecord[] {
  if (due === "today") return records.filter(isFollowupDueToday);
  if (due === "overdue") return records.filter(isFollowupOverdue);
  if (due === "upcoming") return records.filter((record) => isFollowupUpcoming(record));
  if (due === "48h") return records.filter((record) => isFollowupDueWithinHours(record, 48));
  if (due === "missed") return records.filter((record) => isFollowupMissed(record));
  return records;
}

export function countFollowupsDueToday(records: FollowupRecord[]): number {
  return records.filter(isFollowupDueToday).length;
}

export function countFollowupsOverdue(records: FollowupRecord[]): number {
  return records.filter(isFollowupOverdue).length;
}

export function countFollowupsUpcoming(records: FollowupRecord[]): number {
  return records.filter((record) => isFollowupUpcoming(record)).length;
}

export function countFollowupsDueWithinHours(records: FollowupRecord[], hours: number = 48): number {
  return records.filter((record) => isFollowupDueWithinHours(record, hours)).length;
}

export function countFollowupsMissed(records: FollowupRecord[]): number {
  return records.filter((record) => isFollowupMissed(record)).length;
}
