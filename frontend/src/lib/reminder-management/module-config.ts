/**
 * Reminder Management module configuration — loaded from backend metadata APIs.
 *
 * Reminder UI must not hardcode Insurance / Claims / trigger fields.
 * Modules come from GET /reminders/modules; schemas from GET /reminders/modules/{id}/schema.
 */

import { apiClient } from "../api/client";
import type {
  ReminderModuleConfig,
  ReminderModuleKey,
  ReminderModuleSummary,
  ReminderTriggerKind,
} from "./types";

export async function listReminderModules(): Promise<
  Array<{ value: ReminderModuleKey; label: string; supportsDate: boolean; supportsWorkflow: boolean }>
> {
  const modules = await apiClient.listReminderModules();
  return modules.map((item: ReminderModuleSummary) => ({
    value: item.id,
    label: item.name,
    supportsDate: item.supports_date,
    supportsWorkflow: item.supports_workflow,
  }));
}

export async function getReminderModuleConfig(module: ReminderModuleKey): Promise<ReminderModuleConfig> {
  const [modules, schema] = await Promise.all([
    apiClient.listReminderModules(),
    apiClient.getReminderModuleSchema(module),
  ]);
  const summary = modules.find((item) => item.id === module);

  const dateTriggers = (schema.trigger_types ?? []).map((item) => ({
    key: item.key,
    label: item.label,
    kind: "date" as ReminderTriggerKind,
  }));
  const workflowTriggers = (schema.workflow_events ?? []).map((item) => ({
    key: item.key,
    label: item.label,
    kind: "workflow" as ReminderTriggerKind,
  }));

  return {
    module,
    label: summary?.name ?? module,
    triggers: [...dateTriggers, ...workflowTriggers],
    supportedChannels: schema.supported_channels ?? [],
    defaultTemplate: schema.default_template ?? null,
    supportsDate: summary?.supports_date ?? dateTriggers.length > 0,
    supportsWorkflow: summary?.supports_workflow ?? workflowTriggers.length > 0,
  };
}

export function resolveTriggerLabel(
  config: ReminderModuleConfig | null | undefined,
  triggerKey: string,
  fallback = triggerKey
): string {
  return config?.triggers.find((item) => item.key === triggerKey)?.label ?? fallback;
}
