/**
 * Claims-module reminder settings catalog and API mapping.
 * Keep trigger / recipient labels isolated to Claims — do not reuse elsewhere.
 * Channel options come from the shared Generic Reminder channel catalog.
 */

import {
  DEFAULT_REMINDER_CHANNEL,
  getReminderChannelOption,
  parseReminderChannelKey,
  REMINDER_CHANNEL_OPTIONS,
  type ReminderChannelKey,
} from "../reminders/channels";

export const CLAIMS_REMINDER_ENTITY_TYPE = "claims";

/** Sentinel entity id for org-level Claims Reminder Settings (not a Service Case). */
export const CLAIMS_REMINDER_SETTINGS_ENTITY_ID = 0;

export const CLAIMS_REMINDER_TEMPLATE_KEY = "claims_workflow_reminder";

export type ClaimsReminderTriggerKey =
  | "pending_submission"
  | "return_pending"
  | "submitted"
  | "approved";

export type ClaimsReminderRecipientKey = "store_staff" | "store_manager" | "md";

export type ClaimsReminderChannelKey = ReminderChannelKey;

export type ClaimsOffsetUnit = "hours" | "days" | "weeks";

export type ClaimsTimingDirection = "before" | "after";

export type ClaimsReminderTriggerOption = {
  key: ClaimsReminderTriggerKey;
  label: string;
};

export type ClaimsReminderRecipientOption = {
  key: ClaimsReminderRecipientKey;
  label: string;
};

export type ClaimsReminderChannelOption = {
  key: ClaimsReminderChannelKey;
  label: string;
  apiChannel: string;
};

export type ClaimsOffsetUnitOption = {
  key: ClaimsOffsetUnit;
  label: string;
};

/** Claims workflow triggers shown in Reminder Settings. */
export const CLAIMS_REMINDER_TRIGGERS: readonly ClaimsReminderTriggerOption[] = [
  { key: "pending_submission", label: "Pending Submission" },
  { key: "return_pending", label: "Return Pending" },
  { key: "submitted", label: "Submitted" },
  { key: "approved", label: "Approved" },
] as const;

export const CLAIMS_REMINDER_RECIPIENTS: readonly ClaimsReminderRecipientOption[] = [
  { key: "store_staff", label: "Store Staff" },
  { key: "store_manager", label: "Store Manager" },
  { key: "md", label: "MD" },
] as const;

/** All Generic Reminder Engine channels (shared catalog — not Claims-only). */
export const CLAIMS_REMINDER_CHANNELS: readonly ClaimsReminderChannelOption[] =
  REMINDER_CHANNEL_OPTIONS;

export const CLAIMS_REMINDER_OFFSET_UNITS: readonly ClaimsOffsetUnitOption[] = [
  { key: "hours", label: "Hours" },
  { key: "days", label: "Days" },
  { key: "weeks", label: "Weeks" },
] as const;

export type ClaimsReminderFormValues = {
  triggerKey: ClaimsReminderTriggerKey;
  direction: ClaimsTimingDirection;
  offsetValue: number;
  offsetUnit: ClaimsOffsetUnit;
  channelKey: ClaimsReminderChannelKey;
  recipientKey: ClaimsReminderRecipientKey;
  enabled: boolean;
};

export type ClaimsReminderRuleView = {
  configId: number;
  triggerKey: ClaimsReminderTriggerKey;
  triggerLabel: string;
  direction: ClaimsTimingDirection;
  offsetValue: number;
  offsetUnit: ClaimsOffsetUnit;
  channelKey: ClaimsReminderChannelKey;
  channelLabel: string;
  apiChannel: string;
  recipientKey: ClaimsReminderRecipientKey;
  recipientLabel: string;
  enabled: boolean;
};

export const DEFAULT_CLAIMS_REMINDER_FORM: ClaimsReminderFormValues = {
  triggerKey: "pending_submission",
  direction: "after",
  offsetValue: 24,
  offsetUnit: "hours",
  channelKey: DEFAULT_REMINDER_CHANNEL,
  recipientKey: "store_staff",
  enabled: true,
};

function recipientStorageKey(organizationId: number): string {
  return `atm:claims-reminder-recipients:${organizationId}`;
}

export function loadClaimsRecipientMap(organizationId: number): Record<string, ClaimsReminderRecipientKey> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(recipientStorageKey(organizationId));
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, string>;
    const allowed = new Set(CLAIMS_REMINDER_RECIPIENTS.map((item) => item.key));
    const result: Record<string, ClaimsReminderRecipientKey> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (allowed.has(value as ClaimsReminderRecipientKey)) {
        result[key] = value as ClaimsReminderRecipientKey;
      }
    }
    return result;
  } catch {
    return {};
  }
}

export function saveClaimsRecipient(
  organizationId: number,
  configId: number,
  recipientKey: ClaimsReminderRecipientKey
): void {
  if (typeof window === "undefined") return;
  const current = loadClaimsRecipientMap(organizationId);
  current[String(configId)] = recipientKey;
  window.localStorage.setItem(recipientStorageKey(organizationId), JSON.stringify(current));
}

export function removeClaimsRecipient(organizationId: number, configId: number): void {
  if (typeof window === "undefined") return;
  const current = loadClaimsRecipientMap(organizationId);
  delete current[String(configId)];
  window.localStorage.setItem(recipientStorageKey(organizationId), JSON.stringify(current));
}

export function getTriggerLabel(key: string): string {
  return CLAIMS_REMINDER_TRIGGERS.find((item) => item.key === key)?.label ?? key;
}

export function getRecipientLabel(key: string): string {
  return CLAIMS_REMINDER_RECIPIENTS.find((item) => item.key === key)?.label ?? key;
}

export function getChannelOption(key: ClaimsReminderChannelKey): ClaimsReminderChannelOption {
  return getReminderChannelOption(key);
}

export function parseTriggerKey(anchorKey: string | null | undefined): ClaimsReminderTriggerKey {
  const normalized = (anchorKey || "").trim().toLowerCase();
  const match = CLAIMS_REMINDER_TRIGGERS.find((item) => item.key === normalized);
  return match?.key ?? "pending_submission";
}

export function parseOffsetUnit(unit: string | null | undefined): ClaimsOffsetUnit {
  const normalized = (unit || "hours").trim().toLowerCase();
  if (normalized === "days" || normalized === "weeks" || normalized === "hours") {
    return normalized;
  }
  return "hours";
}

export function parseDirection(value: string | null | undefined): ClaimsTimingDirection {
  return (value || "").trim().toLowerCase() === "before" ? "before" : "after";
}

export function parseChannelKey(channels: string[] | string | null | undefined): ClaimsReminderChannelKey {
  return parseReminderChannelKey(channels);
}

/** Map Claims UI form → Generic Reminder API fields (hidden from the user). */
export function mapClaimsFormToApiReminder(form: ClaimsReminderFormValues) {
  const channel = getChannelOption(form.channelKey);
  return {
    channels: [channel.apiChannel],
    offset_value: form.offsetValue,
    offset_unit: form.offsetUnit,
    anchor_type: "workflow" as const,
    anchor_key: form.triggerKey,
    offset_direction: form.direction,
  };
}

export function formatOffsetSummary(value: number, unit: ClaimsOffsetUnit): string {
  const label = CLAIMS_REMINDER_OFFSET_UNITS.find((item) => item.key === unit)?.label ?? unit;
  const singular = label.endsWith("s") ? label.slice(0, -1) : label;
  return `${value} ${value === 1 ? singular : label}`;
}

export type ClaimsReminderGroupRecord = {
  config_id: number;
  organization_id: number;
  entity_type: string;
  entity_id: number;
  anchor_type?: string;
  anchor_key?: string;
  offset_direction?: string;
  offset_value: number;
  offset_unit: string;
  time_of_day?: string | null;
  channels: string[];
  is_active: boolean;
};

export function mapApiGroupToClaimsRule(
  group: ClaimsReminderGroupRecord,
  recipientMap: Record<string, ClaimsReminderRecipientKey>
): ClaimsReminderRuleView {
  const triggerKey = parseTriggerKey(group.anchor_key);
  const channelKey = parseChannelKey(group.channels);
  const channel = getChannelOption(channelKey);
  const recipientKey = recipientMap[String(group.config_id)] ?? "store_staff";
  const offsetUnit = parseOffsetUnit(group.offset_unit);

  return {
    configId: group.config_id,
    triggerKey,
    triggerLabel: getTriggerLabel(triggerKey),
    direction: parseDirection(group.offset_direction),
    offsetValue: group.offset_value,
    offsetUnit,
    channelKey,
    channelLabel: channel.label,
    apiChannel: channel.apiChannel,
    recipientKey,
    recipientLabel: getRecipientLabel(recipientKey),
    enabled: Boolean(group.is_active),
  };
}

export function ruleToFormValues(rule: ClaimsReminderRuleView): ClaimsReminderFormValues {
  return {
    triggerKey: rule.triggerKey,
    direction: rule.direction,
    offsetValue: rule.offsetValue,
    offsetUnit: rule.offsetUnit,
    channelKey: rule.channelKey,
    recipientKey: rule.recipientKey,
    enabled: rule.enabled,
  };
}
