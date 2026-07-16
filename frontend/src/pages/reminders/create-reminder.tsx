import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { ReminderRecipientFields } from "../../components/reminder-management/ReminderRecipientFields";
import { ReminderSchedulingFields } from "../../components/reminder-management/ReminderSchedulingFields";
import Combobox from "../../components/ui/Combobox";
import MultiSelect from "../../components/ui/MultiSelect";
import { InsuranceDatePicker } from "../../components/ui/insurance-date-picker";
import { Button } from "../../components/ui/button";
import { useToast } from "../../components/ui/toast";
import { resolveApiErrorMessage } from "../../lib/api/errors";
import { PERMISSIONS } from "../../lib/auth/permissions";
import {
  displayDateFromIso,
  isoDateFromDisplay,
  validateDisplayDate,
} from "../../lib/utils/date-display";
import {
  comboboxClassName,
  fieldClassName,
  labelClassName,
  REMINDER_OFFSET_UNIT_OPTIONS,
} from "../../lib/reminder-management/constants";
import {
  useReminderModuleConfig,
  useReminderModules,
} from "../../lib/reminder-management/hooks";
import { useReminderModuleContext } from "../../lib/reminder-management/module-context";
import { toTriggerComboboxItems } from "../../lib/reminder-management/module-config";
import { getRemindersBasePath } from "../../lib/reminder-management/paths";
import { createRelativeReminderConfig } from "../../lib/reminder-management/relative-config-api";
import { channelsNeedRecipientFields } from "../../lib/reminder-management/recipient-fields";
import type { ReminderStopCondition } from "../../lib/reminder-management/types";
import { REMINDER_CHANNEL_OPTIONS } from "../../lib/reminders/channels";
import {
  emptyPersonalReminderDraft,
  reminderToDraft,
  validatePersonalReminderDraft,
} from "../../lib/personal-reminders/api";
import {
  useCreatePersonalReminder,
  usePersonalReminder,
  useUpdatePersonalReminder,
} from "../../lib/personal-reminders/hooks";
import type {
  PersonalReminderDraft,
  PersonalReminderTriggerType,
} from "../../lib/personal-reminders/types";
import { useReminderTemplateDefinitions } from "../../lib/reminder-templates/hooks";

const compactTextareaClassName =
  "w-full resize-y rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-3 py-2 min-h-[56px] text-sm font-medium text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors";

const helperTextClassName = "mt-1 text-[11px] leading-snug text-slate-500 dark:text-slate-500";

const sectionHeadingCompactClassName =
  "mb-3 flex items-center gap-2 text-sm font-semibold tracking-tight text-slate-900 dark:text-white md:text-base";

function FormSection({
  title,
  children,
  first = false,
}: {
  title: string;
  children: ReactNode;
  first?: boolean;
}) {
  return (
    <section
      className={first ? "" : "mt-5 border-t border-slate-300/50 dark:border-white/[0.08] pt-5"}
    >
      <h3 className={sectionHeadingCompactClassName}>
        <span className="inline-block h-3.5 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
        {title}
      </h3>
      {children}
    </section>
  );
}

const CHANNEL_OPTIONS = REMINDER_CHANNEL_OPTIONS.map((option) => ({
  value: option.key,
  label: option.label,
}));

const OFFSET_UNIT_OPTIONS = REMINDER_OFFSET_UNIT_OPTIONS.filter(
  (option) => option.value !== "minutes"
);

export function CreateReminderPage() {
  const { reminderId } = useParams<{ reminderId?: string }>();
  const isEdit = Boolean(reminderId);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const base = getRemindersBasePath(pathname);
  const { showToast } = useToast();
  const { hasPermission, organizationId } = useWorkbench();
  const moduleContext = useReminderModuleContext();
  const canCreate = hasPermission(PERMISSIONS.remindersCreate);
  const canUpdate = hasPermission(PERMISSIONS.remindersUpdate);
  const canSave = isEdit ? canUpdate : canCreate;

  const existingQuery = usePersonalReminder(reminderId);
  const definitionsQuery = useReminderTemplateDefinitions({ isActive: true });
  const modulesQuery = useReminderModules();
  const createMutation = useCreatePersonalReminder();
  const updateMutation = useUpdatePersonalReminder();
  const [relativeSaving, setRelativeSaving] = useState(false);

  const [draft, setDraft] = useState<PersonalReminderDraft>(() =>
    emptyPersonalReminderDraft({
      moduleKey: moduleContext.moduleKey ?? "",
    })
  );
  /** Display value for themed date picker (DD-MM-YYYY); draft stores ISO YYYY-MM-DD. */
  const [reminderDateDisplay, setReminderDateDisplay] = useState(() =>
    displayDateFromIso(emptyPersonalReminderDraft().reminderDate) ?? ""
  );
  const [reminderDateError, setReminderDateError] = useState<string | null>(null);

  useEffect(() => {
    if (existingQuery.data) {
      const next = reminderToDraft(existingQuery.data);
      setDraft({ ...next, triggerType: "one_time" });
      setReminderDateDisplay(displayDateFromIso(next.reminderDate) ?? "");
      setReminderDateError(null);
    }
  }, [existingQuery.data]);

  useEffect(() => {
    if (isEdit) return;
    if (!moduleContext.moduleKey) return;
    setDraft((current) =>
      current.moduleKey === moduleContext.moduleKey
        ? current
        : { ...current, moduleKey: moduleContext.moduleKey ?? "" }
    );
  }, [isEdit, moduleContext.moduleKey]);

  const selectedModuleKey = draft.moduleKey.trim();
  const moduleConfigQuery = useReminderModuleConfig(selectedModuleKey);
  const moduleConfig = moduleConfigQuery.data;

  const stopConditionOptions = useMemo(() => {
    const fromApi = moduleConfig?.stopConditions ?? [];
    if (fromApi.length > 0) {
      return fromApi.map((item) => ({ value: item.id, label: item.label }));
    }
    return [];
  }, [moduleConfig?.stopConditions]);

  useEffect(() => {
    if (draft.triggerType !== "relative") return;
    if (!moduleConfig) return;

    const triggers = moduleConfig.triggers;
    if (triggers.length === 0) return;

    const current = triggers.find((item) => item.key === draft.triggerKey);
    if (current) {
      if (draft.triggerKind !== current.kind) {
        setDraft((prev) => ({ ...prev, triggerKind: current.kind }));
      }
      return;
    }

    const first = triggers[0];
    setDraft((prev) => ({
      ...prev,
      triggerKey: first.key,
      triggerKind: first.kind,
    }));
  }, [draft.triggerType, draft.triggerKey, draft.triggerKind, moduleConfig]);

  useEffect(() => {
    if (draft.triggerType !== "relative" || !draft.repeatEnabled) return;
    if (stopConditionOptions.length === 0) return;
    const valid = stopConditionOptions.some((item) => item.value === draft.stopCondition);
    if (!valid) {
      setDraft((prev) => ({
        ...prev,
        stopCondition: stopConditionOptions[0].value as ReminderStopCondition,
      }));
    }
  }, [draft.triggerType, draft.repeatEnabled, draft.stopCondition, stopConditionOptions]);

  const showRecipientInformation = channelsNeedRecipientFields(draft.channels);

  const sharedPhoneNumber = draft.mobileNumber || draft.whatsappNumber;
  const definitions = definitionsQuery.data?.items ?? [];

  /** Map any stored channel-variant template_id onto the logical definition id. */
  const selectedDefinitionId = useMemo(() => {
    if (!draft.templateId) return "";
    const match = definitions.find(
      (definition) =>
        definition.id === draft.templateId || definition.template_ids.includes(draft.templateId)
    );
    return match?.id ?? draft.templateId;
  }, [definitions, draft.templateId]);

  const moduleOptions = useMemo(
    () =>
      (modulesQuery.data ?? []).map((item) => ({
        value: item.value,
        label: item.label,
      })),
    [modulesQuery.data]
  );

  const triggerOptions = useMemo(() => toTriggerComboboxItems(moduleConfig), [moduleConfig]);

  function patchDraft(patch: Partial<PersonalReminderDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function setTriggerType(next: PersonalReminderTriggerType) {
    patchDraft({
      triggerType: next,
      ...(next === "relative" && !draft.moduleKey && moduleContext.moduleKey
        ? { moduleKey: moduleContext.moduleKey }
        : {}),
    });
  }

  async function handleSave() {
    if (!canSave) {
      showToast("You do not have permission to save reminders.", "error");
      return;
    }

    if (draft.triggerType === "one_time") {
      const dateError = validateDisplayDate(reminderDateDisplay);
      if (dateError) {
        setReminderDateError(dateError);
        showToast(dateError, "error");
        return;
      }
      const isoDate = isoDateFromDisplay(reminderDateDisplay);
      if (!isoDate) {
        setReminderDateError("Please enter a valid reminder date.");
        showToast("Please enter a valid reminder date.", "error");
        return;
      }

      const error = validatePersonalReminderDraft({ ...draft, reminderDate: isoDate });
      if (error) {
        showToast(error, "error");
        return;
      }

      const payload: PersonalReminderDraft = {
        ...draft,
        reminderDate: isoDate,
        templateId: selectedDefinitionId || draft.templateId,
        ...(isEdit ? {} : { isActive: true }),
      };

      if (payload.templateId) {
        const selected = definitions.find(
          (definition) =>
            definition.id === payload.templateId ||
            definition.template_ids.includes(payload.templateId)
        );
        if (selected) {
          const missing = draft.channels
            .map((channel) => channel.toLowerCase())
            .filter((channel) => !selected.channels.includes(channel));
          if (missing.length > 0) {
            showToast(
              `Template "${selected.name}" has no content for: ${missing.join(", ")}. Add channel variants on the Templates page.`,
              "error"
            );
            return;
          }
        }
      }

      try {
        if (isEdit && reminderId) {
          await updateMutation.mutateAsync({ id: reminderId, draft: payload });
          showToast("Reminder updated.", "success");
        } else {
          await createMutation.mutateAsync(payload);
          showToast("Reminder created.", "success");
        }
        navigate(base);
      } catch (error) {
        showToast(resolveApiErrorMessage(error, "Failed to save reminder"), "error");
      }
      return;
    }

    // Relative — persist into reminder_configs via Generic Reminder Engine APIs.
    if (isEdit) {
      showToast("Relative scheduling cannot be applied to an existing one-time reminder.", "error");
      return;
    }

    if (organizationId == null) {
      showToast("Organization is not loaded.", "error");
      return;
    }

    const error = validatePersonalReminderDraft(draft);
    if (error) {
      showToast(error, "error");
      return;
    }

    setRelativeSaving(true);
    try {
      await createRelativeReminderConfig({
        organizationId,
        draft: {
          ...draft,
          templateId: selectedDefinitionId || draft.templateId,
          isActive: true,
        },
        templateKey: selectedDefinitionId || draft.templateId,
      });
      showToast("Reminder created.", "success");
      navigate(base);
    } catch (error) {
      showToast(resolveApiErrorMessage(error, "Failed to save reminder"), "error");
    } finally {
      setRelativeSaving(false);
    }
  }

  if (isEdit && existingQuery.isLoading) {
    return (
      <DashboardLayout>
        <LoadingState label="Loading reminder…" />
      </DashboardLayout>
    );
  }

  if (isEdit && existingQuery.isError) {
    return (
      <DashboardLayout>
        <SectionCard eyebrow="Reminder Management" title="Edit Reminder">
          <p className="text-sm text-rose-300">
            {resolveApiErrorMessage(existingQuery.error, "Failed to load reminder.")}
          </p>
          <Button className="mt-4" variant="outline" onClick={() => navigate(base)}>
            Back to list
          </Button>
        </SectionCard>
      </DashboardLayout>
    );
  }

  if (isEdit && existingQuery.isFetched && !existingQuery.data) {
    return (
      <DashboardLayout>
        <SectionCard eyebrow="Reminder Management" title="Edit Reminder">
          <p className="text-sm text-slate-400">Reminder not found.</p>
          <Button className="mt-4" variant="outline" onClick={() => navigate(base)}>
            Back to list
          </Button>
        </SectionCard>
      </DashboardLayout>
    );
  }

  const saving =
    createMutation.isPending || updateMutation.isPending || relativeSaving;

  return (
    <DashboardLayout>
      <SectionCard
        eyebrow="Reminder Management"
        title={isEdit ? "Edit Reminder" : "Create Reminder"}
      >
        <div className="space-y-0">
          <FormSection title="Basic Details" first>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={`block min-w-0 ${isEdit ? "sm:col-span-1" : "sm:col-span-2"}`}>
                <span className={labelClassName}>Reminder Name *</span>
                <input
                  className={fieldClassName}
                  value={draft.title}
                  onChange={(event) => patchDraft({ title: event.target.value })}
                  placeholder="e.g. Call client about renewal"
                />
              </label>
              {isEdit ? (
                <div className="flex flex-col justify-end">
                  <span className={labelClassName}>Active</span>
                  <label className="flex h-12 items-center justify-between gap-3 rounded-xl border border-slate-300/90 bg-white/90 px-3 dark:border-white/10 dark:bg-slate-950/40">
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      Eligible to send when due
                    </span>
                    <input
                      type="checkbox"
                      className="h-4 w-4 shrink-0 rounded border-slate-300 text-[#14B8A6] accent-[#14B8A6] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40"
                      checked={draft.isActive}
                      onChange={(event) => patchDraft({ isActive: event.target.checked })}
                      aria-label="Active"
                    />
                  </label>
                </div>
              ) : null}
            </div>
          </FormSection>

          <FormSection title="Reminder Schedule">
            <div className="space-y-4">
              <fieldset>
                <legend className={labelClassName}>Trigger Type</legend>
                <div className="flex flex-wrap gap-5">
                  {(
                    [
                      { value: "one_time", label: "One Time" },
                      { value: "relative", label: "Relative" },
                    ] as const
                  ).map((option) => (
                    <label
                      key={option.value}
                      className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-gray-800 dark:text-slate-200"
                    >
                      <input
                        type="radio"
                        name="reminder-trigger-type"
                        className="h-4 w-4 accent-[#14B8A6]"
                        checked={draft.triggerType === option.value}
                        disabled={isEdit && option.value === "relative"}
                        onChange={() => setTriggerType(option.value)}
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
              </fieldset>

              {draft.triggerType === "one_time" ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <InsuranceDatePicker
                    label="Reminder Date *"
                    value={reminderDateDisplay}
                    onChange={(next) => {
                      setReminderDateDisplay(next);
                      setReminderDateError(null);
                      const iso = isoDateFromDisplay(next);
                      if (iso) {
                        patchDraft({ reminderDate: iso });
                      } else if (!next.trim()) {
                        patchDraft({ reminderDate: "" });
                      }
                    }}
                    onBlur={() => setReminderDateError(validateDisplayDate(reminderDateDisplay))}
                    error={reminderDateError}
                    labelClassName={labelClassName}
                    inputClassName={fieldClassName}
                  />
                  <label className="block">
                    <span className={labelClassName}>Reminder Time *</span>
                    <input
                      type="time"
                      className={fieldClassName}
                      value={draft.reminderTime}
                      onChange={(event) => patchDraft({ reminderTime: event.target.value })}
                    />
                  </label>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    {!moduleContext.locked ? (
                      <label className="block min-w-0">
                        <span className={labelClassName}>Module *</span>
                        <Combobox
                          items={moduleOptions}
                          value={draft.moduleKey || null}
                          onChange={(next) =>
                            patchDraft({
                              moduleKey: next || "",
                              triggerKey: "",
                            })
                          }
                          placeholder={
                            modulesQuery.isLoading ? "Loading modules…" : "Select module"
                          }
                          searchable
                          className={comboboxClassName}
                        />
                      </label>
                    ) : null}
                    <label
                      className={`block min-w-0 ${moduleContext.locked ? "sm:col-span-2" : ""}`}
                    >
                      <span className={labelClassName}>Trigger *</span>
                      <Combobox
                        items={triggerOptions}
                        value={draft.triggerKey || null}
                        onChange={(next) => {
                          const selected = moduleConfig?.triggers.find((item) => item.key === next);
                          patchDraft({
                            triggerKey: next || "",
                            triggerKind: selected?.kind ?? draft.triggerKind,
                          });
                        }}
                        placeholder={
                          !selectedModuleKey
                            ? "Select a module first"
                            : moduleConfigQuery.isLoading
                              ? "Loading triggers…"
                              : "Select trigger"
                        }
                        searchable
                        className={comboboxClassName}
                      />
                    </label>
                  </div>

                  <ReminderSchedulingFields
                    value={{
                      offsetValue: draft.offsetValue,
                      offsetUnit: draft.offsetUnit,
                      offsetDirection: draft.offsetDirection,
                      repeatEnabled: draft.repeatEnabled,
                      repeatFrequencyValue: draft.repeatFrequencyValue,
                      repeatFrequencyUnit: draft.repeatFrequencyUnit,
                      maxAttempts: draft.maxAttempts,
                      stopCondition: draft.stopCondition as ReminderStopCondition,
                    }}
                    onChange={(patch) => {
                      patchDraft({
                        ...(patch.offsetValue !== undefined
                          ? { offsetValue: patch.offsetValue }
                          : {}),
                        ...(patch.offsetUnit !== undefined
                          ? {
                              offsetUnit: patch.offsetUnit as PersonalReminderDraft["offsetUnit"],
                            }
                          : {}),
                        ...(patch.offsetDirection !== undefined
                          ? { offsetDirection: patch.offsetDirection }
                          : {}),
                        ...(patch.repeatEnabled !== undefined
                          ? { repeatEnabled: patch.repeatEnabled }
                          : {}),
                        ...(patch.repeatFrequencyValue !== undefined
                          ? { repeatFrequencyValue: patch.repeatFrequencyValue }
                          : {}),
                        ...(patch.repeatFrequencyUnit !== undefined
                          ? {
                              repeatFrequencyUnit:
                                patch.repeatFrequencyUnit as PersonalReminderDraft["repeatFrequencyUnit"],
                            }
                          : {}),
                        ...(patch.maxAttempts !== undefined
                          ? { maxAttempts: patch.maxAttempts }
                          : {}),
                        ...(patch.stopCondition !== undefined
                          ? { stopCondition: patch.stopCondition }
                          : {}),
                      });
                    }}
                    offsetUnitOptions={OFFSET_UNIT_OPTIONS}
                    stopConditionOptions={stopConditionOptions}
                    limitsMode="with-recurring"
                    enableRecurringLabel="Enable Recurring"
                  />
                  {draft.repeatEnabled && selectedModuleKey && stopConditionOptions.length === 0 ? (
                    <p className={helperTextClassName}>
                      {moduleConfigQuery.isLoading
                        ? "Loading stop conditions…"
                        : "No stop conditions returned for this module yet."}
                    </p>
                  ) : null}
                </div>
              )}
            </div>
          </FormSection>

          <FormSection title="Channels">
            <MultiSelect
              variant="compact"
              items={CHANNEL_OPTIONS}
              value={draft.channels}
              onChange={(next) => patchDraft({ channels: next })}
            />
          </FormSection>

          {showRecipientInformation ? (
            <FormSection title="Recipient Information">
              <ReminderRecipientFields
                channels={draft.channels}
                values={{
                  phone: sharedPhoneNumber,
                  email: draft.email,
                  telegramChatId: draft.telegramChatId,
                }}
                onChange={(patch) => {
                  if (patch.phone !== undefined) {
                    // Shared phone for SMS + WhatsApp — keep both draft fields in sync.
                    patchDraft({ mobileNumber: patch.phone, whatsappNumber: patch.phone });
                  }
                  if (patch.email !== undefined) {
                    patchDraft({ email: patch.email });
                  }
                  if (patch.telegramChatId !== undefined) {
                    patchDraft({ telegramChatId: patch.telegramChatId });
                  }
                }}
              />
            </FormSection>
          ) : null}

          <FormSection title="Reminder Template">
            <label className="block min-w-0">
              <span className={labelClassName}>Reminder Template</span>
              <Combobox
                items={[
                  { value: "", label: "No template" },
                  ...definitions.map((definition) => ({
                    value: definition.id,
                    label: definition.name,
                  })),
                ]}
                value={selectedDefinitionId || null}
                onChange={(next) => patchDraft({ templateId: next || "" })}
                placeholder={
                  definitionsQuery.isLoading
                    ? "Loading templates…"
                    : "Select a reminder template"
                }
                searchable
                className={comboboxClassName}
              />
              <p className={helperTextClassName}>
                One template is used for all selected channels; each channel gets its own content.
              </p>
            </label>
          </FormSection>

          <FormSection title="Custom Message">
            <label className="block min-w-0">
              <span className={labelClassName}>Custom Message</span>
              <textarea
                className={compactTextareaClassName}
                rows={2}
                value={draft.customMessage}
                onChange={(event) => patchDraft({ customMessage: event.target.value })}
                placeholder="Optional message body when no template is selected"
              />
            </label>
          </FormSection>

          <div className="mt-5 flex flex-wrap items-center justify-end gap-3 border-t border-slate-300/50 dark:border-white/[0.08] pt-4">
            <Button variant="outline" onClick={() => navigate(base)}>
              Cancel
            </Button>
            <Button onClick={() => void handleSave()} disabled={!canSave || saving}>
              {saving ? "Saving…" : "Save Reminder"}
            </Button>
          </div>
        </div>
      </SectionCard>
    </DashboardLayout>
  );
}
