import { getReminderChannelLabel } from "../reminders/channels";
import { buildSchedulePreview } from "./constants";
import type {
  ManagedReminder,
  ReminderHistoryStatus,
  ReminderModuleKey,
  ReminderStatus,
} from "./types";

const moduleLabelCache = new Map<string, string>();

export function rememberModuleLabel(id: string, label: string) {
  if (id && label) moduleLabelCache.set(id, label);
}

export function moduleLabel(module: ReminderModuleKey | string): string {
  if (!module) return "—";
  return moduleLabelCache.get(module) ?? module;
}

export function triggerKindLabel(kind: string): string {
  if (kind === "date") return "Date";
  if (kind === "workflow") return "Workflow";
  return kind;
}

export function formatSchedule(reminder: ManagedReminder): string {
  return buildSchedulePreview({
    offsetValue: reminder.offsetValue,
    offsetUnit: reminder.offsetUnit,
    offsetDirection: reminder.offsetDirection,
    triggerLabel: reminder.triggerLabel || reminder.triggerKey,
  });
}

export function formatChannels(channels: string[]): string {
  if (!channels.length) return "—";
  return channels.map((channel) => getReminderChannelLabel(channel)).join(", ");
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function statusToneClass(status: ReminderStatus | ReminderHistoryStatus | string): string {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "active" || normalized === "sent") {
    return "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30";
  }
  if (normalized === "disabled" || normalized === "skipped" || normalized === "cancelled") {
    return "bg-slate-500/15 text-slate-300 ring-slate-500/30";
  }
  if (normalized === "failed") {
    return "bg-rose-500/15 text-rose-300 ring-rose-500/30";
  }
  if (normalized === "pending" || normalized === "draft") {
    return "bg-amber-500/15 text-amber-200 ring-amber-500/30";
  }
  return "bg-slate-500/15 text-slate-300 ring-slate-500/30";
}
