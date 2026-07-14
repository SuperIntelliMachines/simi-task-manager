import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import Combobox from "../../components/ui/Combobox";
import MultiSelect from "../../components/ui/MultiSelect";
import { Button } from "../../components/ui/button";
import { useToast } from "../../components/ui/toast";
import { resolveApiErrorMessage } from "../../lib/api/errors";
import { PERMISSIONS } from "../../lib/auth/permissions";
import {
  REMINDER_DIRECTION_OPTIONS,
  REMINDER_OFFSET_UNIT_OPTIONS,
  REMINDER_TRIGGER_KIND_OPTIONS,
  buildSchedulePreview,
  comboboxClassName,
  emptyReminderDraft,
  fieldClassName,
  labelClassName,
  sectionHeadingClassName,
  textareaClassName,
} from "../../lib/reminder-management/constants";
import {
  useCreateManagedReminder,
  useManagedReminder,
  useReminderCatalogTemplates,
  useReminderChannels,
  useReminderModuleConfig,
  useReminderModules,
  useUpdateManagedReminder,
} from "../../lib/reminder-management/hooks";
import { getRemindersBasePath } from "../../lib/reminder-management/paths";
import { moduleLabel, rememberModuleLabel } from "../../lib/reminder-management/format";
import { useReminderModuleContext } from "../../lib/reminder-management/module-context";
import type {
  ReminderDraft,
  ReminderModuleKey,
  ReminderOffsetDirection,
  ReminderOffsetUnit,
  ReminderRecipientTarget,
  ReminderTriggerKind,
} from "../../lib/reminder-management/types";

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
    <section className={first ? "" : "mt-8 border-t border-slate-300/60 dark:border-white/[0.08] pt-8"}>
      <h3 className={sectionHeadingClassName}>
        <span className="inline-block h-4 w-1 shrink-0 rounded-full bg-[#14B8A6]" aria-hidden />
        {title}
      </h3>
      {children}
    </section>
  );
}

function reminderToDraft(
  reminder: NonNullable<ReturnType<typeof useManagedReminder>["data"]>
): ReminderDraft {
  return emptyReminderDraft({
    name: reminder.name,
    description: reminder.description,
    module: reminder.module,
    triggerKind: reminder.triggerKind,
    triggerKey: reminder.triggerKey,
    offsetValue: reminder.offsetValue,
    offsetUnit: reminder.offsetUnit,
    offsetDirection: reminder.offsetDirection,
    recipients: reminder.recipients,
    channels: reminder.channels,
    templateId: reminder.templateId ?? "",
    enabled: reminder.enabled,
  });
}

export function CreateReminderPage() {
  const { reminderId } = useParams<{ reminderId?: string }>();
  const isEdit = Boolean(reminderId);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const base = getRemindersBasePath(pathname);
  const { showToast } = useToast();
  const { hasPermission } = useWorkbench();
  const moduleContext = useReminderModuleContext();
  const canCreate = hasPermission(PERMISSIONS.remindersCreate);
  const canUpdate = hasPermission(PERMISSIONS.remindersUpdate);
  const canSave = isEdit ? canUpdate : canCreate;

  const existingQuery = useManagedReminder(reminderId);
  const modulesQuery = useReminderModules();
  const catalogTemplatesQuery = useReminderCatalogTemplates();
  const channelsQuery = useReminderChannels();
  const createMutation = useCreateManagedReminder();
  const updateMutation = useUpdateManagedReminder();

  const [draft, setDraft] = useState<ReminderDraft>(() =>
    emptyReminderDraft({
      module: moduleContext.locked && moduleContext.moduleKey ? moduleContext.moduleKey : "",
    })
  );
  const moduleConfigQuery = useReminderModuleConfig(draft.module);

  useEffect(() => {
    if (existingQuery.data) setDraft(reminderToDraft(existingQuery.data));
  }, [existingQuery.data]);

  const moduleOptions = modulesQuery.data ?? [];

  // Locked workspace (Insurance/Claims/Inventory): force create-flow module_key.
  useEffect(() => {
    if (isEdit || !moduleContext.locked || !moduleContext.moduleKey) return;
    setDraft((current) => {
      if (current.module === moduleContext.moduleKey) return current;
      return {
        ...current,
        module: moduleContext.moduleKey!,
        triggerKey: "",
        recipients: [],
      };
    });
  }, [isEdit, moduleContext.locked, moduleContext.moduleKey]);

  // Global Reminder Management: default to first registered module once metadata loads.
  useEffect(() => {
    if (isEdit || moduleContext.locked || draft.module || moduleOptions.length === 0) return;
    setDraft((current) => ({
      ...current,
      module: moduleOptions[0].value,
      triggerKey: "",
      recipients: [],
    }));
  }, [isEdit, moduleContext.locked, draft.module, moduleOptions]);

  for (const option of moduleOptions) {
    rememberModuleLabel(option.value, option.label);
  }

  const lockedModuleLabel =
    moduleOptions.find((option) => option.value === draft.module)?.label ??
    moduleLabel(draft.module);

  const moduleConfig = moduleConfigQuery.data;
  const triggersForKind = useMemo(
    () => (moduleConfig?.triggers ?? []).filter((item) => item.kind === draft.triggerKind),
    [moduleConfig, draft.triggerKind]
  );
  const recipientOptions = moduleConfig?.recipients ?? [];

  const triggerKindOptions = useMemo(() => {
    return REMINDER_TRIGGER_KIND_OPTIONS.filter((option) => {
      if (option.value === "date") return moduleConfig?.supportsDate !== false;
      if (option.value === "workflow") return moduleConfig?.supportsWorkflow !== false;
      return true;
    });
  }, [moduleConfig]);

  const channelOptions = useMemo(() => {
    const fromModule = moduleConfig?.supportedChannels ?? [];
    const fromPlatform = channelsQuery.data ?? [];
    const keys = fromModule.length > 0 ? fromModule : fromPlatform.map((item) => item.key);
    return keys.map((key) => {
      const match = fromPlatform.find((item) => item.key === key);
      return match ?? { key, label: key, apiChannel: key };
    });
  }, [moduleConfig, channelsQuery.data]);

  // Keep triggerKey valid when module or kind changes.
  useEffect(() => {
    if (!moduleConfig) return;
    const available = moduleConfig.triggers.filter((item) => item.kind === draft.triggerKind);
    if (!available.some((item) => item.key === draft.triggerKey)) {
      setDraft((current) => ({
        ...current,
        triggerKey: available[0]?.key ?? "",
      }));
    }
  }, [moduleConfig, draft.triggerKind, draft.triggerKey]);

  // Drop recipients that are no longer offered by the selected module.
  useEffect(() => {
    if (!moduleConfig) return;
    const allowed = new Set(moduleConfig.recipients.map((item) => item.id));
    setDraft((current) => {
      const next = current.recipients.filter((item) => allowed.has(item.id));
      if (next.length === current.recipients.length) return current;
      return { ...current, recipients: next };
    });
  }, [moduleConfig]);

  const selectedTriggerLabel =
    triggersForKind.find((item) => item.key === draft.triggerKey)?.label ?? draft.triggerKey;

  const schedulePreview = buildSchedulePreview({
    offsetValue: draft.offsetValue,
    offsetUnit: draft.offsetUnit,
    offsetDirection: draft.offsetDirection,
    triggerLabel: selectedTriggerLabel,
  });

  const templates = useMemo(() => {
    const catalog = catalogTemplatesQuery.data ?? [];
    return catalog.filter(
      (template) => !template.module || template.module === "any" || template.module === draft.module
    );
  }, [catalogTemplatesQuery.data, draft.module]);

  function patchDraft(patch: Partial<ReminderDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function setRecipientsFromIds(ids: string[]) {
    const byId = new Map(recipientOptions.map((item) => [item.id, item]));
    const next: ReminderRecipientTarget[] = ids.map((id) => {
      const match = byId.get(id);
      return match ?? { id, label: id };
    });
    patchDraft({ recipients: next });
  }

  function validate(): string | null {
    if (!draft.module) return "Select a module.";
    if (!draft.name.trim()) return "Reminder name is required.";
    if (!draft.triggerKey) return "Select a trigger.";
    if (!draft.offsetValue || draft.offsetValue <= 0) return "Offset value must be greater than zero.";
    if (draft.recipients.length === 0) return "Select at least one recipient.";
    if (draft.channels.length === 0) return "Select at least one channel.";
    if (!draft.templateId) return "Select a template.";
    return null;
  }

  async function handleSave() {
    if (!canSave) {
      showToast("You do not have permission to save reminders.", "error");
      return;
    }
    const error = validate();
    if (error) {
      showToast(error, "error");
      return;
    }
    try {
      if (isEdit && reminderId) {
        await updateMutation.mutateAsync({ id: reminderId, draft });
        showToast("Reminder updated.", "success");
      } else {
        await createMutation.mutateAsync(draft);
        showToast("Reminder created.", "success");
      }
      navigate(base);
    } catch (error) {
      showToast(resolveApiErrorMessage(error, "Failed to save reminder"), "error");
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

  if (isEdit && existingQuery.data === null) {
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

  return (
    <DashboardLayout>
      <SectionCard
        eyebrow="Reminder Management"
        title={isEdit ? "Edit Reminder" : "Create Reminder"}
      >
        <div className="space-y-0">
          {moduleContext.locked ? (
            draft.module ? (
              <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
                Applying to{" "}
                <span className="font-medium text-slate-900 dark:text-slate-200">
                  {lockedModuleLabel}
                </span>
                . Trigger and recipient options load from this module&apos;s configuration.
              </p>
            ) : null
          ) : (
            <FormSection title="Module" first>
              <label className="block max-w-md">
                <span className={labelClassName}>Applies to</span>
                <Combobox
                  items={moduleOptions.map((option) => ({
                    value: option.value,
                    label: option.label,
                  }))}
                  value={draft.module || null}
                  onChange={(next) => {
                    const module = (next || "") as ReminderModuleKey;
                    patchDraft({ module, triggerKey: "", recipients: [] });
                  }}
                  placeholder={modulesQuery.isLoading ? "Loading modules…" : "Select module"}
                  searchable
                  className={comboboxClassName}
                />
              </label>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Trigger and recipient options are loaded from this module&apos;s configuration.
              </p>
            </FormSection>
          )}

          <FormSection title="Basic Details" first={moduleContext.locked}>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className={labelClassName}>Reminder Name *</span>
                <input
                  className={fieldClassName}
                  value={draft.name}
                  onChange={(event) => patchDraft({ name: event.target.value })}
                  placeholder="e.g. Pending approval follow-up"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className={labelClassName}>Description</span>
                <textarea
                  className={textareaClassName}
                  value={draft.description}
                  onChange={(event) => patchDraft({ description: event.target.value })}
                  placeholder="Optional context for operators"
                />
              </label>
            </div>
          </FormSection>

          <FormSection title="Trigger">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className={labelClassName}>Trigger Type</span>
                <Combobox
                  items={triggerKindOptions.map((option) => ({
                    value: option.value,
                    label: option.label,
                  }))}
                  value={draft.triggerKind}
                  onChange={(next) =>
                    patchDraft({
                      triggerKind: (next || "date") as ReminderTriggerKind,
                      triggerKey: "",
                    })
                  }
                  placeholder="Select trigger type"
                  searchable={false}
                  className={comboboxClassName}
                />
              </label>
              <label className="block">
                <span className={labelClassName}>Trigger</span>
                <Combobox
                  items={triggersForKind.map((option) => ({
                    value: option.key,
                    label: option.label,
                  }))}
                  value={draft.triggerKey || null}
                  onChange={(next) => patchDraft({ triggerKey: next || "" })}
                  placeholder={
                    moduleConfigQuery.isLoading ? "Loading triggers…" : "Select trigger"
                  }
                  searchable
                  className={comboboxClassName}
                />
              </label>
            </div>
          </FormSection>

          <FormSection title="Schedule">
            <div className="grid gap-4 sm:grid-cols-3">
              <label className="block">
                <span className={labelClassName}>Offset Value</span>
                <input
                  type="number"
                  min={1}
                  className={fieldClassName}
                  value={draft.offsetValue}
                  onChange={(event) =>
                    patchDraft({ offsetValue: Number(event.target.value) || 0 })
                  }
                />
              </label>
              <label className="block">
                <span className={labelClassName}>Offset Unit</span>
                <Combobox
                  items={[...REMINDER_OFFSET_UNIT_OPTIONS]}
                  value={draft.offsetUnit}
                  onChange={(next) =>
                    patchDraft({
                      offsetUnit: (next || "days") as ReminderOffsetUnit,
                    })
                  }
                  placeholder="Select unit"
                  searchable={false}
                  className={comboboxClassName}
                />
              </label>
              <label className="block">
                <span className={labelClassName}>Direction</span>
                <Combobox
                  items={[...REMINDER_DIRECTION_OPTIONS]}
                  value={draft.offsetDirection}
                  onChange={(next) =>
                    patchDraft({
                      offsetDirection: (next || "before") as ReminderOffsetDirection,
                    })
                  }
                  placeholder="Select direction"
                  searchable={false}
                  className={comboboxClassName}
                />
              </label>
            </div>
            <div className="mt-4 rounded-xl border border-[#14B8A6]/25 bg-gradient-to-r from-[#8B5CF6]/10 to-[#14B8A6]/10 px-4 py-3 text-sm text-slate-800 dark:text-slate-100">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0f766e] dark:text-[#99f6e4]">
                Preview
              </span>
              <div className="mt-1 font-medium">{schedulePreview}</div>
            </div>
          </FormSection>

          <FormSection title="Recipients">
            {moduleConfigQuery.isLoading ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">Loading recipients…</p>
            ) : recipientOptions.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                No recipients configured for this module.
              </p>
            ) : (
              <MultiSelect
                items={recipientOptions.map((option) => ({
                  value: option.id,
                  label: option.label,
                }))}
                value={draft.recipients.map((item) => item.id)}
                onChange={setRecipientsFromIds}
                columns={2}
              />
            )}
          </FormSection>

          <FormSection title="Channels">
            <MultiSelect
              items={channelOptions.map((option) => ({
                value: option.key,
                label: option.label,
              }))}
              value={draft.channels}
              onChange={(channels) =>
                patchDraft({ channels: channels as ReminderDraft["channels"] })
              }
            />
          </FormSection>

          <FormSection title="Template">
            <label className="block max-w-xl">
              <span className={labelClassName}>Template</span>
              <Combobox
                items={templates.map((template) => ({
                  value: template.id,
                  label: `${template.name} (${template.channel})`,
                }))}
                value={draft.templateId || null}
                onChange={(next) => patchDraft({ templateId: next || "" })}
                placeholder="Select a template"
                searchable
                className={comboboxClassName}
              />
            </label>
          </FormSection>

          <FormSection title="Status">
            <label className="flex items-center justify-between gap-4 rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 py-3">
              <div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white">Active</div>
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  Inactive reminders remain in the list but do not schedule.
                </p>
              </div>
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-slate-300 text-[#14B8A6] accent-[#14B8A6] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40"
                checked={draft.enabled}
                onChange={(event) => patchDraft({ enabled: event.target.checked })}
              />
            </label>
          </FormSection>

          <div className="mt-8 flex flex-wrap items-center justify-end gap-3 border-t border-slate-300/60 dark:border-white/[0.08] pt-6">
            <Button variant="outline" onClick={() => navigate(base)}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleSave()}
              disabled={!canSave || createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending ? "Saving…" : "Save Reminder"}
            </Button>
          </div>
        </div>
      </SectionCard>
    </DashboardLayout>
  );
}
