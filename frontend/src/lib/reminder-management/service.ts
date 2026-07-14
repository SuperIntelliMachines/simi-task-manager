import { apiClient } from "../api/client";
import { generalReminderService } from "../../services/generalReminderService";
import type {
  ManagedReminder,
  ReminderDraft,
  ReminderHistoryEntry,
  ReminderHistoryFilters,
  ReminderListFilters,
  ReminderTemplate,
} from "./types";

export type ReminderListPage = {
  items: ManagedReminder[];
  total: number;
  limit: number;
  offset: number;
};

/** Reminder definitions — backed by GET/POST/PUT/DELETE /general-reminders. */
export const reminderManagementApi = {
  async listReminders(
    filters?: Partial<ReminderListFilters> & { limit?: number; offset?: number }
  ): Promise<ReminderListPage> {
    return generalReminderService.listReminders(filters);
  },

  async getReminder(id: string): Promise<ManagedReminder | null> {
    try {
      return await generalReminderService.getReminder(id);
    } catch (error) {
      const status = (error as { status?: number })?.status;
      if (status === 404) return null;
      throw error;
    }
  },

  async createReminder(draft: ReminderDraft): Promise<ManagedReminder> {
    return generalReminderService.createReminder(draft);
  },

  async updateReminder(id: string, draft: ReminderDraft): Promise<ManagedReminder> {
    return generalReminderService.updateReminder(id, draft);
  },

  async setReminderEnabled(id: string, enabled: boolean): Promise<ManagedReminder> {
    return generalReminderService.setReminderEnabled(id, enabled);
  },

  async deleteReminder(id: string): Promise<void> {
    return generalReminderService.deleteReminder(id);
  },

  /** Templates: catalog from metadata API only (no localStorage). */
  async listTemplates(): Promise<ReminderTemplate[]> {
    const catalog = await apiClient.listReminderCatalogTemplates();
    return catalog.map((item) => ({
      id: item.id,
      name: item.name,
      channel: item.channel as ReminderTemplate["channel"],
      subject: item.subject,
      body: item.body,
      module: (item.module ?? "any") as ReminderTemplate["module"],
      createdAt: "",
      updatedAt: "",
    }));
  },

  async createTemplate(
    _input: Omit<ReminderTemplate, "id" | "createdAt" | "updatedAt">
  ): Promise<ReminderTemplate> {
    throw new Error("Custom reminder templates are not available yet. Use catalog templates.");
  },

  async updateTemplate(_id: string, _patch: Partial<ReminderTemplate>): Promise<ReminderTemplate> {
    throw new Error("Custom reminder templates are not available yet.");
  },

  async deleteTemplate(_id: string): Promise<void> {
    throw new Error("Custom reminder templates are not available yet.");
  },

  /** Execution history is not part of general reminder definitions. */
  async listHistory(_filters?: Partial<ReminderHistoryFilters>): Promise<ReminderHistoryEntry[]> {
    return [];
  },

  async testReminder(_id: string): Promise<ReminderHistoryEntry> {
    throw new Error("Test send is not available for general reminder definitions.");
  },
};
