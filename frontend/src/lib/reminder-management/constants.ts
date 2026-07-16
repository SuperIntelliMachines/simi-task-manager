import { REMINDER_CHANNEL_OPTIONS } from "../reminders/channels";
import type {
  ReminderDraft,
  ReminderHistoryStatus,
  ReminderOffsetDirection,
  ReminderOffsetUnit,
  ReminderRecurrenceUnit,
  ReminderStatus,
  ReminderStopCondition,
  ReminderTriggerKind,
} from "./types";

/** Shared with Insurance create/edit forms — do not invent a separate Reminder theme. */
export const labelClassName =
  "mb-1.5 block text-sm font-medium text-gray-800 dark:text-slate-300";

export const fieldClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 h-12 text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";

export const comboboxClassName =
  "h-12 w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-3 text-sm font-medium text-gray-800 dark:text-white hover:border-[#14B8A6]/40 transition-colors";

export const textareaClassName =
  "w-full rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 py-3 min-h-[100px] text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";

export const sectionHeadingClassName =
  "mb-5 flex items-center gap-3 text-base font-semibold tracking-tight text-slate-900 dark:text-white md:text-lg";

/** @deprecated Use sectionHeadingClassName — kept for any stray imports. */
export const sectionTitleClassName = sectionHeadingClassName;

export const REMINDER_STATUS_OPTIONS: ReadonlyArray<{ value: ReminderStatus; label: string }> = [
  { value: "active", label: "Active" },
  { value: "disabled", label: "Disabled" },
];

export const REMINDER_TRIGGER_KIND_OPTIONS: ReadonlyArray<{
  value: ReminderTriggerKind;
  label: string;
}> = [
  { value: "date", label: "Date" },
  { value: "workflow", label: "Workflow" },
];

export const REMINDER_OFFSET_UNIT_OPTIONS: ReadonlyArray<{ value: ReminderOffsetUnit; label: string }> = [
  { value: "minutes", label: "Minutes" },
  { value: "hours", label: "Hours" },
  { value: "days", label: "Days" },
  { value: "weeks", label: "Weeks" },
  { value: "months", label: "Months" },
];

export const REMINDER_DIRECTION_OPTIONS: ReadonlyArray<{
  value: ReminderOffsetDirection;
  label: string;
}> = [
  { value: "before", label: "Before" },
  { value: "after", label: "After" },
];

export const REMINDER_HISTORY_STATUS_OPTIONS: ReadonlyArray<{
  value: ReminderHistoryStatus;
  label: string;
}> = [
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
  { value: "pending", label: "Pending" },
  { value: "skipped", label: "Skipped" },
];

/** Fallback labels while /reminders/channels loads — keys still come from API when available. */
export const REMINDER_CHANNEL_FILTER_OPTIONS = REMINDER_CHANNEL_OPTIONS.map((option) => ({
  value: option.key,
  label: option.label,
}));

export const REMINDER_RECURRENCE_UNIT_OPTIONS: ReadonlyArray<{
  value: ReminderRecurrenceUnit;
  label: string;
}> = [
  { value: "hours", label: "Hours" },
  { value: "days", label: "Days" },
  { value: "weeks", label: "Weeks" },
  { value: "months", label: "Months" },
];

export const REMINDER_STOP_CONDITION_OPTIONS: ReadonlyArray<{
  value: ReminderStopCondition;
  label: string;
}> = [
  { value: "entity_ineligible", label: "Entity No Longer Matches Trigger" },
  { value: "workflow_status_changed", label: "Workflow Status Changes" },
  { value: "end_date_reached", label: "End Date Reached" },
  { value: "max_attempts_reached", label: "Maximum Attempts Reached" },
  { value: "never", label: "Never (continue until manually disabled)" },
];

export function emptyReminderDraft(defaults?: Partial<ReminderDraft>): ReminderDraft {
  return {
    name: "",
    description: "",
    module: "",
    triggerKind: "date",
    triggerKey: "",
    offsetValue: 30,
    offsetUnit: "days",
    offsetDirection: "before",
    repeatEnabled: false,
    repeatFrequencyValue: 24,
    repeatFrequencyUnit: "hours",
    maxAttempts: null,
    stopCondition: "entity_ineligible",
    channels: ["in_app"],
    templateId: "",
    enabled: true,
    ...defaults,
  };
}

export function buildSchedulePreview(input: {
  offsetValue: number;
  offsetUnit: ReminderOffsetUnit;
  offsetDirection: ReminderOffsetDirection;
  triggerLabel: string;
}): string {
  const unitLabel =
    REMINDER_OFFSET_UNIT_OPTIONS.find((option) => option.value === input.offsetUnit)?.label ??
    input.offsetUnit;
  const directionLabel =
    REMINDER_DIRECTION_OPTIONS.find((option) => option.value === input.offsetDirection)?.label ??
    input.offsetDirection;
  const trigger = input.triggerLabel.trim() || "selected trigger";
  return `${input.offsetValue} ${unitLabel} ${directionLabel} ${trigger}`;
}
