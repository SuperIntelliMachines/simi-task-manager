/** Types for Personal Reminder CRUD (independent of Reminder Definitions). */

export type PersonalReminderStatus = "PENDING" | "SENT" | "FAILED" | "CANCELLED";

export type PersonalReminderChannel =
  | "in_app"
  | "email"
  | "sms"
  | "whatsapp"
  | "telegram"
  | string;

export type PersonalReminder = {
  id: string;
  organization_id: number;
  created_by: number;
  title: string;
  description: string | null;
  scheduled_at: string;
  channels: string[];
  email: string | null;
  mobile_number: string | null;
  whatsapp_number: string | null;
  telegram_chat_id: string | null;
  template_id: string | null;
  custom_message: string | null;
  status: PersonalReminderStatus | string;
  sent_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PersonalReminderUpsert = {
  title: string;
  description?: string | null;
  scheduled_at: string;
  channels: string[];
  email?: string | null;
  mobile_number?: string | null;
  whatsapp_number?: string | null;
  telegram_chat_id?: string | null;
  template_id?: string | null;
  custom_message?: string | null;
  status?: PersonalReminderStatus;
  is_active?: boolean;
};

export type PersonalReminderListResponse = {
  items: PersonalReminder[];
  total: number;
  limit: number;
  offset: number;
};

export type PersonalReminderListFilters = {
  search: string;
  status: PersonalReminderStatus | "all";
  channel: string | "all";
  isActive: boolean | "all";
  page: number;
  pageSize: number;
};

/** UI schedule mode on Create Reminder — One Time uses date/time; Relative uses offset config. */
export type PersonalReminderTriggerType = "one_time" | "relative";

export type RelativeReminderOffsetUnit = "hours" | "days" | "weeks" | "months";
export type RelativeReminderOffsetDirection = "before" | "after";

/** One relative offset row for the same module trigger. */
export type RelativeReminderRule = {
  /** Client-side row id for list rendering (not persisted). */
  id: string;
  offsetValue: number;
  offsetUnit: RelativeReminderOffsetUnit;
  offsetDirection: RelativeReminderOffsetDirection;
};

export type PersonalReminderDraft = {
  title: string;
  /** YYYY-MM-DD — used when triggerType is one_time */
  reminderDate: string;
  /** HH:mm — used when triggerType is one_time */
  reminderTime: string;
  /** one_time = personal absolute schedule; relative = module offset / recurrence */
  triggerType: PersonalReminderTriggerType;
  /** Reminder engine module_key when triggerType is relative (from metadata). */
  moduleKey: string;
  /** Module trigger field / workflow event key when relative. */
  triggerKey: string;
  /** date | workflow — mirrors module trigger kind. */
  triggerKind: "date" | "workflow";
  /**
   * Relative offset rows for the selected trigger.
   * Legacy single-offset fields below mirror the first row for compatibility.
   */
  relativeRules: RelativeReminderRule[];
  offsetValue: number;
  offsetUnit: RelativeReminderOffsetUnit;
  offsetDirection: RelativeReminderOffsetDirection;
  repeatEnabled: boolean;
  repeatFrequencyValue: number;
  repeatFrequencyUnit: "hours" | "days" | "weeks" | "months";
  maxAttempts: number | null;
  stopCondition: string;
  channels: string[];
  email: string;
  mobileNumber: string;
  whatsappNumber: string;
  telegramChatId: string;
  templateId: string;
  customMessage: string;
  isActive: boolean;
};
