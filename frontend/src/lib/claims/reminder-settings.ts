/**
 * Claims-module reminder settings catalog and API mapping.
 * Triggers come from GET /reminders/modules/claims/schema via useReminderModuleConfig.
 * Channel options come from the shared Generic Reminder channel catalog.
 */

import {
  DEFAULT_REMINDER_CHANNEL,
  getReminderChannelOption,
  parseReminderChannelKey,
  REMINDER_CHANNEL_OPTIONS,
  type ReminderChannelKey,
} from "../reminders/channels";
import { resolveTriggerLabel } from "../reminder-management/module-config";
import type {
  ReminderModuleConfig,
  ReminderStopCondition,
  ReminderTriggerKind,
} from "../reminder-management/types";

export const CLAIMS_REMINDER_ENTITY_TYPE = "claims";

/** Sentinel entity id for org-level Claims Reminder Settings (not a Service Case). */
export const CLAIMS_REMINDER_SETTINGS_ENTITY_ID = 0;

export const CLAIMS_REMINDER_TEMPLATE_KEY = "claims_workflow_reminder";

export type ClaimsReminderRecipientKey = "store_staff" | "store_manager" | "md";

export type ClaimsReminderChannelKey = ReminderChannelKey;

export type ClaimsOffsetUnit = "hours" | "days" | "weeks" | "months";

export type ClaimsTimingDirection = "before" | "after";

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
  { key: "months", label: "Months" },
] as const;

export type ClaimsReminderFormValues = {
  /** Metadata trigger key from module schema (anchor_key). */
  triggerKey: string;
  /** Metadata trigger kind from module schema (anchor_type). */
  triggerKind: ReminderTriggerKind;
  direction: ClaimsTimingDirection;
  offsetValue: number;
  offsetUnit: ClaimsOffsetUnit;
  channelKey: ClaimsReminderChannelKey;
  recipientKey: ClaimsReminderRecipientKey;
  enabled: boolean;
  repeatEnabled: boolean;
  repeatFrequencyValue: number;
  repeatFrequencyUnit: ClaimsOffsetUnit;
  maxAttempts: number | null;
  stopCondition: ReminderStopCondition;
};

export type ClaimsReminderRuleView = {
  configId: number;
  triggerKey: string;
  triggerKind: ReminderTriggerKind;
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
  repeatEnabled: boolean;
  repeatFrequencyValue: number;
  repeatFrequencyUnit: ClaimsOffsetUnit;
  maxAttempts: number | null;
  stopCondition: ReminderStopCondition;
};

/** Base defaults without a hardcoded trigger — apply first metadata trigger via buildDefaultClaimsReminderForm. */
export const DEFAULT_CLAIMS_REMINDER_FORM: ClaimsReminderFormValues = {
  triggerKey: "",
  triggerKind: "workflow",
  direction: "after",
  offsetValue: 24,
  offsetUnit: "hours",
  channelKey: DEFAULT_REMINDER_CHANNEL,
  recipientKey: "store_staff",
  enabled: true,
  repeatEnabled: false,
  repeatFrequencyValue: 24,
  repeatFrequencyUnit: "hours",
  maxAttempts: null,
  stopCondition: "workflow_status_changed",
};

/** Default form using the first trigger from module metadata (same source as Create Reminder). */
export function buildDefaultClaimsReminderForm(
  moduleConfig: ReminderModuleConfig | null | undefined
): ClaimsReminderFormValues {
  const first = moduleConfig?.triggers[0];
  return {
    ...DEFAULT_CLAIMS_REMINDER_FORM,
    triggerKey: first?.key ?? "",
    triggerKind: first?.kind ?? "workflow",
  };
}

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

export function getRecipientLabel(key: string): string {
  return CLAIMS_REMINDER_RECIPIENTS.find((item) => item.key === key)?.label ?? key;
}

export function getChannelOption(key: ClaimsReminderChannelKey): ClaimsReminderChannelOption {
  return getReminderChannelOption(key);
}

export function parseOffsetUnit(unit: string | null | undefined): ClaimsOffsetUnit {
  const normalized = (unit || "hours").trim().toLowerCase();
  if (
    normalized === "days" ||
    normalized === "weeks" ||
    normalized === "hours" ||
    normalized === "months"
  ) {
    return normalized;
  }
  return "hours";
}

function parseStopCondition(value: string | null | undefined): ReminderStopCondition {
  const normalized = (value || "entity_ineligible").trim().toLowerCase();
  if (
    normalized === "never" ||
    normalized === "entity_ineligible" ||
    normalized === "workflow_status_changed" ||
    normalized === "end_date_reached" ||
    normalized === "max_attempts_reached"
  ) {
    return normalized;
  }
  return "entity_ineligible";
}

function parseTriggerKind(value: string | null | undefined): ReminderTriggerKind {
  return (value || "").trim().toLowerCase() === "date" ? "date" : "workflow";
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
    anchor_type: form.triggerKind,
    anchor_key: form.triggerKey.trim(),
    offset_direction: form.direction,
    repeat_enabled: form.repeatEnabled,
    repeat_frequency_value: form.repeatEnabled ? form.repeatFrequencyValue : null,
    repeat_frequency_unit: form.repeatEnabled ? form.repeatFrequencyUnit : null,
    max_attempts: form.maxAttempts,
    stop_condition: form.stopCondition,
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
  repeat_enabled?: boolean;
  repeat_frequency_value?: number | null;
  repeat_frequency_unit?: string | null;
  max_attempts?: number | null;
  stop_condition?: string;
};

export function mapApiGroupToClaimsRule(
  group: ClaimsReminderGroupRecord,
  recipientMap: Record<string, ClaimsReminderRecipientKey>,
  moduleConfig?: ReminderModuleConfig | null
): ClaimsReminderRuleView {
  const triggerKey = (group.anchor_key || "").trim();
  const triggerKind = parseTriggerKind(group.anchor_type);
  const channelKey = parseChannelKey(group.channels);
  const channel = getChannelOption(channelKey);
  const recipientKey = recipientMap[String(group.config_id)] ?? "store_staff";
  const offsetUnit = parseOffsetUnit(group.offset_unit);

  return {
    configId: group.config_id,
    triggerKey,
    triggerKind,
    triggerLabel: resolveTriggerLabel(moduleConfig, triggerKey),
    direction: parseDirection(group.offset_direction),
    offsetValue: group.offset_value,
    offsetUnit,
    channelKey,
    channelLabel: channel.label,
    apiChannel: channel.apiChannel,
    recipientKey,
    recipientLabel: getRecipientLabel(recipientKey),
    enabled: Boolean(group.is_active),
    repeatEnabled: Boolean(group.repeat_enabled),
    repeatFrequencyValue: group.repeat_frequency_value ?? 24,
    repeatFrequencyUnit: parseOffsetUnit(group.repeat_frequency_unit),
    maxAttempts: group.max_attempts ?? null,
    stopCondition: parseStopCondition(group.stop_condition),
  };
}

export function ruleToFormValues(rule: ClaimsReminderRuleView): ClaimsReminderFormValues {
  return {
    triggerKey: rule.triggerKey,
    triggerKind: rule.triggerKind,
    direction: rule.direction,
    offsetValue: rule.offsetValue,
    offsetUnit: rule.offsetUnit,
    channelKey: rule.channelKey,
    recipientKey: rule.recipientKey,
    enabled: rule.enabled,
    repeatEnabled: rule.repeatEnabled,
    repeatFrequencyValue: rule.repeatFrequencyValue,
    repeatFrequencyUnit: rule.repeatFrequencyUnit,
    maxAttempts: rule.maxAttempts,
    stopCondition: rule.stopCondition,
  };
}
