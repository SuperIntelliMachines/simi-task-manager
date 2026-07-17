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
import type { PersonalReminderDraft, RelativeReminderRule } from "../personal-reminders/types";
import { createRelativeReminderRule } from "./relative-rules";

/** Org-level / module settings sentinel — same pattern as Claims Reminder Settings. */
export const RELATIVE_REMINDER_ORG_ENTITY_ID = 0;

function resolveRelativeRules(draft: PersonalReminderDraft): RelativeReminderRule[] {
  if (draft.relativeRules?.length) {
    return draft.relativeRules;
  }
  // Backward compatibility: single-offset drafts become one row.
  return [
    createRelativeReminderRule({
      offsetValue: draft.offsetValue,
      offsetUnit: draft.offsetUnit,
      offsetDirection: draft.offsetDirection,
    }),
  ];
}

export function draftToReminderConfigDefinitions(
  draft: PersonalReminderDraft
): ReminderDefinitionInput[] {
  const channels = draft.channels.map((channel) => channel.trim().toLowerCase()).filter(Boolean);
  const rules = resolveRelativeRules(draft);

  return rules.map((rule) => ({
    channels,
    offset_value: rule.offsetValue,
    offset_unit: rule.offsetUnit,
    anchor_type: draft.triggerKind,
    anchor_key: draft.triggerKey.trim(),
    offset_direction: rule.offsetDirection,
    repeat_enabled: draft.repeatEnabled,
    repeat_frequency_value: draft.repeatEnabled ? draft.repeatFrequencyValue : null,
    repeat_frequency_unit: draft.repeatEnabled ? draft.repeatFrequencyUnit : null,
    max_attempts: draft.maxAttempts,
    stop_condition: draft.stopCondition || "entity_ineligible",
    stop_condition_config: null,
  }));
}

/** @deprecated Prefer draftToReminderConfigDefinitions for multi-rule saves. */
export function draftToReminderConfigDefinition(
  draft: PersonalReminderDraft
): ReminderDefinitionInput {
  return draftToReminderConfigDefinitions(draft)[0];
}

export function buildRelativeReminderConfigCreateInput(input: {
  organizationId: number;
  draft: PersonalReminderDraft;
  templateKey?: string | null;
}): ReminderConfigCreateInput {
  const { organizationId, draft, templateKey } = input;
  const definitions = draftToReminderConfigDefinitions(draft);
  const trimmedTemplate = (templateKey ?? draft.templateId).trim();

  return {
    organization_id: organizationId,
    entity_type: draft.moduleKey.trim().toLowerCase(),
    entity_id: RELATIVE_REMINDER_ORG_ENTITY_ID,
    reminders: definitions,
    template_key: trimmedTemplate || null,
    entity_label: draft.title.trim() || null,
    // Append — do not deactivate existing Claims / module settings for this entity.
    replace_existing: false,
  };
}

/** Create live ReminderConfig rows for a Relative reminder (engine path). */
export async function createRelativeReminderConfig(input: {
  organizationId: number;
  draft: PersonalReminderDraft;
  templateKey?: string | null;
}): Promise<ReminderConfigGroupListResponse> {
  const payload = buildRelativeReminderConfigCreateInput(input);
  return apiClient.createReminderConfigs(payload);
}
