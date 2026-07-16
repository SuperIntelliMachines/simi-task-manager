/**
 * Reminder History API client — maps to /api/v1/reminder-history.
 */
import { apiClient } from "../api/client";
import type {
  ReminderHistoryDetail,
  ReminderHistoryListFilters,
  ReminderHistoryListResponse,
} from "./types";

/** Build query params for GET /reminder-history (pure; testable). */
export function buildReminderHistoryListParams(
  filters?: Partial<ReminderHistoryListFilters>
): {
  status?: string;
  channel?: string;
  executed_from?: string;
  executed_to?: string;
  search?: string;
  page: number;
  page_size: number;
} {
  const pageSize = filters?.pageSize ?? 50;
  const pageZeroBased = filters?.page ?? 0;
  const page = Math.max(1, pageZeroBased + 1);

  const status =
    filters?.status && filters.status !== "all" ? String(filters.status).toUpperCase() : undefined;
  const channel =
    filters?.channel && filters.channel !== "all"
      ? String(filters.channel).trim().toLowerCase()
      : undefined;
  const search = filters?.search?.trim() || undefined;

  const dateFrom = filters?.dateFrom?.trim();
  const dateTo = filters?.dateTo?.trim();
  const executed_from = dateFrom ? `${dateFrom}T00:00:00` : undefined;
  const executed_to = dateTo ? `${dateTo}T23:59:59` : undefined;

  return {
    status,
    channel,
    executed_from,
    executed_to,
    search,
    page,
    page_size: pageSize,
  };
}

export const reminderHistoryApi = {
  async list(filters?: Partial<ReminderHistoryListFilters>): Promise<ReminderHistoryListResponse> {
    return apiClient.listReminderHistory(buildReminderHistoryListParams(filters));
  },

  async get(id: string): Promise<ReminderHistoryDetail> {
    return apiClient.getReminderHistory(id);
  },
};
