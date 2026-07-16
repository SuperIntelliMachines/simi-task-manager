/** Types for Reminder History read APIs (Reminder Management). */

export type ReminderHistoryStatus = "SENT" | "FAILED" | "SKIPPED" | "PENDING" | string;

export type ReminderHistoryListItem = {
  id: string;
  organization_id: number;
  reminder_id: string | null;
  template_id: string | null;
  created_by: number;
  reminder_title: string;
  channel: string;
  recipient: string;
  status: ReminderHistoryStatus;
  provider_message_id: string | null;
  error_message: string | null;
  executed_at: string;
};

export type ReminderHistoryReminderSummary = {
  id: string;
  title: string;
  status: string;
  scheduled_at: string;
  is_active: boolean;
};

export type ReminderHistoryTemplateSummary = {
  id: string;
  name: string;
  channel: string;
  is_active: boolean;
};

export type ReminderHistoryDetail = ReminderHistoryListItem & {
  created_at: string;
  reminder: ReminderHistoryReminderSummary | null;
  template: ReminderHistoryTemplateSummary | null;
};

export type ReminderHistoryListResponse = {
  items: ReminderHistoryListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type ReminderHistoryListFilters = {
  module: string | "all";
  status: string | "all";
  channel: string | "all";
  dateFrom: string;
  dateTo: string;
  search: string;
  /** 0-based page index for UI; converted to 1-based for the API. */
  page: number;
  pageSize: number;
};
