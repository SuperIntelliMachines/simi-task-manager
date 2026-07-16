import { useQuery } from "@tanstack/react-query";

import { reminderHistoryApi } from "./api";
import type { ReminderHistoryListFilters } from "./types";

const KEYS = {
  list: (filters: Partial<ReminderHistoryListFilters>) =>
    ["reminder-history", "list", filters] as const,
  detail: (id: string) => ["reminder-history", "detail", id] as const,
};

export function useReminderHistory(filters: ReminderHistoryListFilters) {
  return useQuery({
    queryKey: KEYS.list(filters),
    queryFn: () => reminderHistoryApi.list(filters),
  });
}

export function useReminderHistoryDetail(id: string | undefined) {
  return useQuery({
    queryKey: KEYS.detail(id ?? ""),
    queryFn: () => reminderHistoryApi.get(id!),
    enabled: Boolean(id),
  });
}

export { KEYS as reminderHistoryQueryKeys };
