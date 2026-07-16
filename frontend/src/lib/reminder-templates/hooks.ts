import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { reminderTemplateApi } from "./api";
import type { ReminderTemplateDraft, ReminderTemplateListFilters } from "./types";

const KEYS = {
  list: (filters: Partial<ReminderTemplateListFilters>) =>
    ["reminder-templates", "list", filters] as const,
  definitions: (isActive?: boolean) =>
    ["reminder-templates", "definitions", isActive ?? true] as const,
  detail: (id: string) => ["reminder-templates", "detail", id] as const,
};

export function useReminderTemplates(filters?: Partial<ReminderTemplateListFilters>) {
  return useQuery({
    queryKey: KEYS.list(filters ?? {}),
    queryFn: () => reminderTemplateApi.list(filters),
  });
}

export function useReminderTemplateDefinitions(options?: { isActive?: boolean }) {
  const isActive = options?.isActive ?? true;
  return useQuery({
    queryKey: KEYS.definitions(isActive),
    queryFn: () => reminderTemplateApi.listDefinitions({ isActive }),
  });
}

export function useReminderTemplate(id: string | undefined) {
  return useQuery({
    queryKey: KEYS.detail(id ?? ""),
    queryFn: () => reminderTemplateApi.get(id!),
    enabled: Boolean(id),
  });
}

export function useCreateReminderTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draft: ReminderTemplateDraft) => reminderTemplateApi.create(draft),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-templates"] });
    },
  });
}

export function useUpdateReminderTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, draft }: { id: string; draft: ReminderTemplateDraft }) =>
      reminderTemplateApi.update(id, draft),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-templates"] });
      void queryClient.invalidateQueries({ queryKey: KEYS.detail(variables.id) });
    },
  });
}

export function useDeleteReminderTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reminderTemplateApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminder-templates"] });
    },
  });
}
