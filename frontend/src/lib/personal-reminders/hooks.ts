import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { personalReminderApi } from "./api";
import type { PersonalReminderDraft, PersonalReminderListFilters } from "./types";

const KEYS = {
  list: (filters: Partial<PersonalReminderListFilters>) =>
    ["personal-reminders", "list", filters] as const,
  detail: (id: string) => ["personal-reminders", "detail", id] as const,
  catalogTemplates: ["personal-reminders", "catalog-templates"] as const,
};

export function usePersonalReminders(filters: PersonalReminderListFilters) {
  return useQuery({
    queryKey: KEYS.list(filters),
    queryFn: () =>
      personalReminderApi.list({
        ...filters,
        limit: filters.pageSize,
        offset: filters.page * filters.pageSize,
      }),
  });
}

export function usePersonalReminder(id: string | undefined) {
  return useQuery({
    queryKey: KEYS.detail(id ?? ""),
    queryFn: () => personalReminderApi.get(id!),
    enabled: Boolean(id),
  });
}

export function usePersonalReminderCatalogTemplates() {
  return useQuery({
    queryKey: KEYS.catalogTemplates,
    queryFn: () => apiClient.listReminderCatalogTemplates(),
  });
}

export function useCreatePersonalReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draft: PersonalReminderDraft) => personalReminderApi.create(draft),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["personal-reminders"] });
    },
  });
}

export function useUpdatePersonalReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, draft }: { id: string; draft: PersonalReminderDraft }) =>
      personalReminderApi.update(id, draft),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["personal-reminders"] });
      void queryClient.invalidateQueries({ queryKey: KEYS.detail(variables.id) });
    },
  });
}

export function useTogglePersonalReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      personalReminderApi.setActive(id, isActive),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["personal-reminders"] });
    },
  });
}

export function useDeletePersonalReminder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => personalReminderApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["personal-reminders"] });
    },
  });
}
