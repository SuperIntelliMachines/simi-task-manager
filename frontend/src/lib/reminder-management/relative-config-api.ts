/**
 * Map Create Reminder (Relative) form state onto Generic Reminder Engine configs.
 * Persists via POST /reminders/config → reminder_configs (not reminder_definitions).
 */
import { apiClient } from "../api/client";
import type {
  ReminderConfigCreateInput,
  ReminderDefinitionInput,
  ReminderConfigGroupListResponse,
} from "../api/types";
import type { PersonalReminderDraft } from "../personal-reminders/types";

/** Org-level / module settings sentinel — same pattern as Claims Reminder Settings. */
export const RELATIVE_REMINDER_ORG_ENTITY_ID = 0;

export function draftToReminderConfigDefinition(
  draft: PersonalReminderDraft
): ReminderDefinitionInput {
  return {
    channels: draft.channels.map((channel) => channel.trim().toLowerCase()).filter(Boolean),
    offset_value: draft.offsetValue,
    offset_unit: draft.offsetUnit,
    anchor_type: draft.triggerKind,
    anchor_key: draft.triggerKey.trim(),
    offset_direction: draft.offsetDirection,
    repeat_enabled: draft.repeatEnabled,
    repeat_frequency_value: draft.repeatEnabled ? draft.repeatFrequencyValue : null,
    repeat_frequency_unit: draft.repeatEnabled ? draft.repeatFrequencyUnit : null,
    max_attempts: draft.maxAttempts,
    stop_condition: draft.stopCondition || "entity_ineligible",
    stop_condition_config: null,
  };
}

export function buildRelativeReminderConfigCreateInput(input: {
  organizationId: number;
  draft: PersonalReminderDraft;
  templateKey?: string | null;
}): ReminderConfigCreateInput {
  const { organizationId, draft, templateKey } = input;
  const definition = draftToReminderConfigDefinition(draft);
  const trimmedTemplate = (templateKey ?? draft.templateId).trim();

  return {
    organization_id: organizationId,
    entity_type: draft.moduleKey.trim().toLowerCase(),
    entity_id: RELATIVE_REMINDER_ORG_ENTITY_ID,
    reminders: [definition],
    template_key: trimmedTemplate || null,
    entity_label: draft.title.trim() || null,
    // Append — do not deactivate existing Claims / module settings for this entity.
    replace_existing: false,
  };
}

/** Create a live ReminderConfig for a Relative reminder (engine path). */
export async function createRelativeReminderConfig(input: {
  organizationId: number;
  draft: PersonalReminderDraft;
  templateKey?: string | null;
}): Promise<ReminderConfigGroupListResponse> {
  const payload = buildRelativeReminderConfigCreateInput(input);
  return apiClient.createReminderConfigs(payload);
}
