import { formatDate } from "../utils/formatDate";
import {
  RENEWAL_FREQUENCY_DEFAULT,
  RENEWAL_FREQUENCY_HALF_YEARLY,
  RENEWAL_FREQUENCY_MONTHLY,
  RENEWAL_FREQUENCY_QUARTERLY,
  RENEWAL_FREQUENCY_YEARLY,
} from "./renewal-frequency";

export type ReminderUnit = "hours" | "days" | "weeks" | "months";

export type PersonalizedReminderUnit = ReminderUnit;

export type CustomReminderItem = {
  reminder_unit: ReminderUnit;
  reminder_value: number;
};

export type CustomReminderPreviewLine = {
  label: string;
  previewDate: string;
};

export type ReminderType = "default" | "personalized";

export const REMINDER_TYPE_OPTIONS: Array<{ value: ReminderType; label: string }> = [
  { value: "default", label: "Default" },
  { value: "personalized", label: "Personalized" },
];

export const DEFAULT_RENEWAL_REMINDER_CYCLE_DAYS = [30, 15, 10, 5, 2, 1, 0] as const;

export const REMINDER_UNIT_OPTIONS: Array<{ value: ReminderUnit; label: string }> = [
  { value: "hours", label: "Hours" },
  { value: "days", label: "Days" },
  { value: "weeks", label: "Weeks" },
  { value: "months", label: "Months" },
];

/** Fixed options for the Renewal Reminders page — never derived from other form state. */
export const RENEWAL_REMINDER_UNIT_SELECT_OPTIONS: ReadonlyArray<{ value: ReminderUnit; label: string }> =
  Object.freeze([
    { value: "hours", label: "Hours" },
    { value: "days", label: "Days" },
    { value: "weeks", label: "Weeks" },
    { value: "months", label: "Months" },
  ]);

export const RENEWAL_REMINDER_UNIT_LABELS = ["Hours", "Days", "Weeks", "Months"] as const;

export function isReminderUnit(value: string): value is ReminderUnit {
  return RENEWAL_REMINDER_UNIT_SELECT_OPTIONS.some((option) => option.value === value);
}

export function sanitizeReminderUnit(value: string): ReminderUnit {
  return isReminderUnit(value) ? value : "days";
}

export const PERSONALIZED_REMINDER_UNIT_OPTIONS: ReadonlyArray<{ value: ReminderUnit; label: string }> =
  Object.freeze([
    { value: "hours", label: "Hours" },
    { value: "days", label: "Days" },
    { value: "weeks", label: "Weeks" },
    { value: "months", label: "Months" },
  ]);

export const PREFERRED_CHANNEL_OPTIONS = [
  { value: "sms", label: "SMS" },
  { value: "telegram", label: "Telegram" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "email", label: "Email" },
] as const;

export function formatPreferredChannelsLabel(channels: string[] | null | undefined): string {
  if (!channels?.length) {
    return "-";
  }

  return channels
    .map((channel) => {
      const match = PREFERRED_CHANNEL_OPTIONS.find((option) => option.value === channel);
      return match?.label ?? channel;
    })
    .join(", ");
}

export type ReminderValueBounds = {
  min: number;
  max: number;
};

export function maxMonthsForRenewalFrequency(frequency: string | null | undefined): number {
  const normalized = (frequency || RENEWAL_FREQUENCY_DEFAULT).trim().toLowerCase();
  switch (normalized) {
    case RENEWAL_FREQUENCY_MONTHLY:
      return 1;
    case RENEWAL_FREQUENCY_QUARTERLY:
      return 3;
    case RENEWAL_FREQUENCY_HALF_YEARLY:
      return 6;
    case RENEWAL_FREQUENCY_YEARLY:
      return 12;
    default:
      return 12;
  }
}

export function getReminderValueBounds(
  unit: ReminderUnit,
  renewalFrequency?: string | null
): ReminderValueBounds {
  switch (unit) {
    case "hours":
      return { min: 1, max: 24 };
    case "days":
      return { min: 1, max: 7 };
    case "weeks":
      return { min: 1, max: 4 };
    case "months":
      return { min: 1, max: maxMonthsForRenewalFrequency(renewalFrequency) };
    default:
      return { min: 1, max: 1 };
  }
}

export function getRenewalReminderValueBounds(unit: ReminderUnit): ReminderValueBounds {
  switch (unit) {
    case "hours":
      return { min: 1, max: 24 };
    case "days":
      return { min: 1, max: 7 };
    case "weeks":
      return { min: 1, max: 4 };
    case "months":
      return { min: 1, max: 12 };
    default:
      return { min: 1, max: 1 };
  }
}

export function validateReminderValue(
  unit: ReminderUnit,
  rawValue: string,
  renewalFrequency?: string | null
): string | null {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return "Reminder value is required.";
  }

  const value = Number(trimmed);
  if (!Number.isInteger(value)) {
    return "Enter a whole number.";
  }

  const { min, max } = getReminderValueBounds(unit, renewalFrequency);
  if (value < min || value > max) {
    return `Enter a value between ${min} and ${max}.`;
  }

  return null;
}

export function validateRenewalReminderValue(unit: ReminderUnit, rawValue: string): string | null {
  const trimmed = rawValue.trim();
  if (!trimmed) {
    return "Reminder value is required.";
  }

  const value = Number(trimmed);
  if (!Number.isInteger(value)) {
    return "Enter a whole number.";
  }

  const { min, max } = getRenewalReminderValueBounds(unit);
  if (value < min || value > max) {
    return `Enter a value between ${min} and ${max}.`;
  }

  return null;
}

export type ReminderPreview = {
  reminderDate: string;
  reminderDay: string;
  reminderTime: string | null;
};

export function computeNextReminderDate(
  expiryDate: string | null | undefined,
  unit: ReminderUnit,
  value: number
): Date | null {
  if (!expiryDate || !Number.isFinite(value) || value <= 0) {
    return null;
  }

  const expiry = new Date(expiryDate);
  if (Number.isNaN(expiry.getTime())) {
    return null;
  }

  const reminder = new Date(expiry.getTime());

  switch (unit) {
    case "hours":
      reminder.setTime(reminder.getTime() - value * 60 * 60 * 1000);
      break;
    case "days":
      reminder.setDate(reminder.getDate() - value);
      break;
    case "weeks":
      reminder.setDate(reminder.getDate() - value * 7);
      break;
    case "months":
      reminder.setDate(reminder.getDate() - value * 30);
      break;
    default:
      return null;
  }

  return reminder;
}

export function computeReminderPreview(
  expiryDate: string | null | undefined,
  unit: ReminderUnit,
  value: number
): ReminderPreview | null {
  const reminder = computeNextReminderDate(expiryDate, unit, value);
  if (!reminder) {
    return null;
  }

  return {
    reminderDate: formatDate(reminder),
    reminderDay: reminder.toLocaleDateString("en-IN", { weekday: "long" }),
    reminderTime:
      unit === "hours"
        ? reminder.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: true,
          })
        : null,
  };
}

export function computePersonalizedReminderPreview(
  expiryDate: string | null | undefined,
  unit: PersonalizedReminderUnit,
  value: number
): { schedule: string; nextReminder: string } | null {
  if (!Number.isInteger(value) || value <= 0) {
    return null;
  }

  const nextReminderDate = computeNextReminderDate(expiryDate, unit, value);
  if (!nextReminderDate) {
    return null;
  }

  return {
    schedule: formatPersonalizedReminderSchedule(unit, value),
    nextReminder: formatPersonalizedNextReminderDate(nextReminderDate, unit),
  };
}

function formatPersonalizedNextReminderDate(date: Date, unit: PersonalizedReminderUnit): string {
  const dateLabel = formatDate(date);
  if (unit !== "hours") {
    return dateLabel;
  }

  const timeLabel = date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
  return `${dateLabel} ${timeLabel}`;
}

export function validateDoNotDisturbWindow(startTime: string, endTime: string): string | null {
  if (!startTime || !endTime) {
    return "Start and end times are required.";
  }
  if (startTime === endTime) {
    return "Start and end times must be different.";
  }
  return null;
}

export function formatReminderUnitWord(unit: ReminderUnit, value: number): string {
  const singular =
    unit === "hours"
      ? "hour"
      : unit === "days"
        ? "day"
        : unit === "weeks"
          ? "week"
          : "month";
  const plural =
    unit === "hours"
      ? "hours"
      : unit === "days"
        ? "days"
        : unit === "weeks"
          ? "weeks"
          : "months";
  return value === 1 ? singular : plural;
}

export function formatCustomReminderBeforeExpiryLabel(unit: ReminderUnit, value: number): string {
  return `${value} ${formatReminderUnitWord(unit, value)} before expiry`;
}

export function formatCustomReminderPreviewDate(date: Date, unit: ReminderUnit): string {
  const dateLabel = date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  if (unit !== "hours") {
    return dateLabel;
  }

  const timeLabel = date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
  return `${dateLabel} ${timeLabel}`;
}

export function customRemindersFromPolicy(policy: {
  custom_reminders?: Array<{
    reminder_unit?: string | null;
    reminder_value?: number | null;
  }> | null;
  reminder_unit?: string | null;
  reminder_value?: number | null;
}): CustomReminderItem[] {
  if (policy.custom_reminders?.length) {
    return policy.custom_reminders
      .map((item) => ({
        reminder_unit: sanitizeReminderUnit(item.reminder_unit ?? "days"),
        reminder_value: Number(item.reminder_value ?? 0),
      }))
      .filter((item) => item.reminder_value > 0);
  }

  if (policy.reminder_unit && policy.reminder_value != null && policy.reminder_value > 0) {
    return [
      {
        reminder_unit: sanitizeReminderUnit(policy.reminder_unit),
        reminder_value: policy.reminder_value,
      },
    ];
  }

  return [];
}

export function validatePersonalizedReminders(reminders: CustomReminderItem[]): string | null {
  if (reminders.length === 0) {
    return "Add at least one personalized reminder.";
  }
  return null;
}

export function computeCustomRemindersPreview(
  expiryDate: string | null | undefined,
  reminders: CustomReminderItem[]
): CustomReminderPreviewLine[] {
  return reminders
    .map((item) => {
      const reminderDate = computeNextReminderDate(expiryDate, item.reminder_unit, item.reminder_value);
      if (!reminderDate) {
        return null;
      }
      return {
        item,
        label: formatCustomReminderBeforeExpiryLabel(item.reminder_unit, item.reminder_value),
        previewDate: formatCustomReminderPreviewDate(reminderDate, item.reminder_unit),
        sortKey: reminderDate.getTime(),
      };
    })
    .filter((line): line is NonNullable<typeof line> => line !== null)
    .sort((left, right) => right.sortKey - left.sortKey)
    .map(({ label, previewDate }) => ({ label, previewDate }));
}

export function buildApiCustomRemindersPayload(reminders: CustomReminderItem[]) {
  return reminders.map((item) => ({
    reminder_unit: item.reminder_unit,
    reminder_value: item.reminder_value,
  }));
}

export function formatPersonalizedReminderSchedule(
  unit: PersonalizedReminderUnit,
  value: number
): string {
  const singular =
    unit === "hours"
      ? "hour"
      : unit === "days"
        ? "day"
        : unit === "weeks"
          ? "week"
          : "month";
  const plural =
    unit === "hours"
      ? "hours"
      : unit === "days"
        ? "days"
        : unit === "weeks"
          ? "weeks"
          : "months";
  const label = value === 1 ? singular : plural;
  return `Reminder will be sent ${value} ${label} before expiry`;
}

export function formatReminderDisplayDate(value: string | Date | null | undefined): string {
  if (!value) return "";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export type PolicyReminderSettingsPayload = {
  reminder_type: ReminderType;
  preferred_channel: string[];
  default_cycle_days?: readonly number[];
  personalized?: {
    unit: PersonalizedReminderUnit;
    value: number;
    do_not_disturb_start: string;
    do_not_disturb_end: string;
  };
};

export function buildPolicyReminderSettingsPayload(input: {
  reminderType: ReminderType;
  preferredChannels: string[];
  personalizedUnit?: PersonalizedReminderUnit;
  personalizedValue?: string;
  doNotDisturbStart?: string;
  doNotDisturbEnd?: string;
}): PolicyReminderSettingsPayload {
  const preferredChannels = input.preferredChannels
    .map((channel) => channel.trim().toLowerCase())
    .filter(Boolean);

  if (input.reminderType === "default") {
    return {
      reminder_type: "default",
      preferred_channel: preferredChannels,
      default_cycle_days: DEFAULT_RENEWAL_REMINDER_CYCLE_DAYS,
    };
  }

  return {
    reminder_type: "personalized",
    preferred_channel: preferredChannels,
    personalized: {
      unit: input.personalizedUnit ?? "days",
      value: Number(input.personalizedValue ?? "0"),
      do_not_disturb_start: input.doNotDisturbStart ?? "",
      do_not_disturb_end: input.doNotDisturbEnd ?? "",
    },
  };
}
