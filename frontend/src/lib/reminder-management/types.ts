import type { ReminderChannelKey } from "../reminders/channels";

/** Module id from GET /reminders/modules (e.g. policy, claims). */
export type ReminderModuleKey = string;

export type ReminderStatus = "active" | "disabled" | "draft";

/** High-level trigger family — Date uses offsets; Workflow uses stage/events. */
export type ReminderTriggerKind = "date" | "workflow";

export type ReminderOffsetUnit = "minutes" | "hours" | "days" | "weeks" | "months";

export type ReminderOffsetDirection = "before" | "after";

export type ReminderHistoryStatus = "sent" | "failed" | "pending" | "skipped";

export type ReminderModuleSummary = {
  id: string;
  name: string;
  supports_date: boolean;
  supports_workflow: boolean;
};

export type ReminderModuleSchema = {
  trigger_types: Array<{ key: string; label: string; type: string }>;
  workflow_events: Array<{ key: string; label: string }>;
  supported_channels: string[];
  default_template?: string | null;
};

export type ReminderCatalogTemplate = {
  id: string;
  name: string;
  channel: string;
  subject: string;
  body: string;
  module?: string | null;
};

/** Trigger option provided by a module configuration/API. */
export type ModuleTriggerOption = {
  key: string;
  label: string;
  kind: ReminderTriggerKind;
};

/** Per-module reminder form configuration (loaded dynamically). */
export type ReminderModuleConfig = {
  module: ReminderModuleKey;
  label: string;
  triggers: ModuleTriggerOption[];
  supportedChannels: string[];
  defaultTemplate?: string | null;
  supportsDate: boolean;
  supportsWorkflow: boolean;
};

export type ManagedReminder = {
  id: string;
  name: string;
  description: string;
  module: ReminderModuleKey;
  /** date | workflow */
  triggerKind: ReminderTriggerKind;
  /** Module-defined trigger key (field or workflow event). */
  triggerKey: string;
  /** Display label snapshot from module config at save time. */
  triggerLabel: string;
  offsetValue: number;
  offsetUnit: ReminderOffsetUnit;
  offsetDirection: ReminderOffsetDirection;
  channels: ReminderChannelKey[];
  templateId?: string | null;
  enabled: boolean;
  status: ReminderStatus;
  nextTriggerAt?: string | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
};

export type ReminderTemplate = {
  id: string;
  name: string;
  channel: ReminderChannelKey;
  subject: string;
  body: string;
  module?: ReminderModuleKey | "any";
  updatedAt: string;
  createdAt: string;
};

export type ReminderHistoryEntry = {
  id: string;
  reminderId: string;
  reminderName: string;
  module: ReminderModuleKey;
  triggerTime: string;
  recipient: string;
  channel: ReminderChannelKey;
  status: ReminderHistoryStatus;
  sentTime?: string | null;
  error?: string | null;
};

export type ReminderDraft = {
  name: string;
  description: string;
  module: ReminderModuleKey;
  triggerKind: ReminderTriggerKind;
  triggerKey: string;
  offsetValue: number;
  offsetUnit: ReminderOffsetUnit;
  offsetDirection: ReminderOffsetDirection;
  channels: ReminderChannelKey[];
  templateId: string;
  enabled: boolean;
};

export type ReminderListFilters = {
  search: string;
  module: ReminderModuleKey | "all";
  status: ReminderStatus | "all";
  channel: ReminderChannelKey | "all";
  /** 0-based page index for server pagination. */
  page: number;
  pageSize: number;
};

export type ReminderHistoryFilters = {
  module: ReminderModuleKey | "all";
  status: ReminderHistoryStatus | "all";
  channel: ReminderChannelKey | "all";
  dateFrom: string;
  dateTo: string;
};
