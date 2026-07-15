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

export type PersonalReminderDraft = {
  title: string;
  description: string;
  /** YYYY-MM-DD */
  reminderDate: string;
  /** HH:mm */
  reminderTime: string;
  channels: string[];
  email: string;
  mobileNumber: string;
  whatsappNumber: string;
  telegramChatId: string;
  templateId: string;
  customMessage: string;
  isActive: boolean;
};
