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
  comboboxClassName,
  fieldClassName,
  labelClassName,
  sectionHeadingClassName,
  textareaClassName,
} from "../../lib/reminder-management/constants";
import { getRemindersBasePath } from "../../lib/reminder-management/paths";
import { REMINDER_CHANNEL_OPTIONS, getReminderChannelLabel } from "../../lib/reminders/channels";
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
import { useReminderTemplates } from "../../lib/reminder-templates/hooks";
import type { PersonalReminderDraft } from "../../lib/personal-reminders/types";

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

const CHANNEL_OPTIONS = REMINDER_CHANNEL_OPTIONS.map((option) => ({
  value: option.key,
  label: option.label,
}));

export function CreateReminderPage() {
  const { reminderId } = useParams<{ reminderId?: string }>();
  const isEdit = Boolean(reminderId);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const base = getRemindersBasePath(pathname);
  const { showToast } = useToast();
  const { hasPermission } = useWorkbench();
  const canCreate = hasPermission(PERMISSIONS.remindersCreate);
  const canUpdate = hasPermission(PERMISSIONS.remindersUpdate);
  const canSave = isEdit ? canUpdate : canCreate;

  const existingQuery = usePersonalReminder(reminderId);
  const templatesQuery = useReminderTemplates({ isActive: true });
  const createMutation = useCreatePersonalReminder();
  const updateMutation = useUpdatePersonalReminder();

  const [draft, setDraft] = useState<PersonalReminderDraft>(() => emptyPersonalReminderDraft());

  useEffect(() => {
    if (existingQuery.data) setDraft(reminderToDraft(existingQuery.data));
  }, [existingQuery.data]);

  const channels = useMemo(
    () => new Set(draft.channels.map((channel) => channel.toLowerCase())),
    [draft.channels]
  );
  const showDeliveryDetails =
    channels.has("email") ||
    channels.has("sms") ||
    channels.has("whatsapp") ||
    channels.has("telegram");

  const templates = templatesQuery.data?.items ?? [];

  function patchDraft(patch: Partial<PersonalReminderDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  async function handleSave() {
    if (!canSave) {
      showToast("You do not have permission to save reminders.", "error");
      return;
    }
    const error = validatePersonalReminderDraft(draft);
    if (error) {
      showToast(error, "error");
      return;
    }

    // When a saved template is selected, copy its body into custom_message if empty.
    let payload = draft;
    const selectedTemplate = templates.find((template) => template.id === draft.templateId);
    if (selectedTemplate && !draft.customMessage.trim()) {
      payload = {
        ...draft,
        customMessage: selectedTemplate.body,
      };
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

  return (
    <DashboardLayout>
      <SectionCard
        eyebrow="Reminder Management"
        title={isEdit ? "Edit Reminder" : "Create Reminder"}
      >
        <div className="space-y-0">
          <FormSection title="Basic Details" first>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className={labelClassName}>Reminder Name *</span>
                <input
                  className={fieldClassName}
                  value={draft.title}
                  onChange={(event) => patchDraft({ title: event.target.value })}
                  placeholder="e.g. Call client about renewal"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className={labelClassName}>Description</span>
                <textarea
                  className={textareaClassName}
                  value={draft.description}
                  onChange={(event) => patchDraft({ description: event.target.value })}
                  placeholder="Optional context"
                />
              </label>
            </div>
          </FormSection>

          <FormSection title="Schedule">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className={labelClassName}>Reminder Date *</span>
                <input
                  type="date"
                  className={fieldClassName}
                  value={draft.reminderDate}
                  onChange={(event) => patchDraft({ reminderDate: event.target.value })}
                />
              </label>
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
          </FormSection>

          <FormSection title="Channels">
            <MultiSelect
              items={CHANNEL_OPTIONS}
              value={draft.channels}
              onChange={(next) => patchDraft({ channels: next })}
            />
          </FormSection>

          {showDeliveryDetails ? (
            <FormSection title="Delivery Details">
              <div className="grid gap-4 sm:grid-cols-2">
                {channels.has("email") ? (
                  <label className="block sm:col-span-2">
                    <span className={labelClassName}>Email Address *</span>
                    <input
                      type="email"
                      className={fieldClassName}
                      value={draft.email}
                      onChange={(event) => patchDraft({ email: event.target.value })}
                      placeholder="name@example.com"
                    />
                  </label>
                ) : null}
                {channels.has("sms") ? (
                  <label className="block">
                    <span className={labelClassName}>Mobile Number *</span>
                    <input
                      className={fieldClassName}
                      value={draft.mobileNumber}
                      onChange={(event) => patchDraft({ mobileNumber: event.target.value })}
                      placeholder="e.g. 9876543210"
                    />
                  </label>
                ) : null}
                {channels.has("whatsapp") ? (
                  <label className="block">
                    <span className={labelClassName}>WhatsApp Number *</span>
                    <input
                      className={fieldClassName}
                      value={draft.whatsappNumber}
                      onChange={(event) => patchDraft({ whatsappNumber: event.target.value })}
                      placeholder="e.g. 919876543210"
                    />
                  </label>
                ) : null}
                {channels.has("telegram") ? (
                  <label className="block sm:col-span-2">
                    <span className={labelClassName}>Telegram Chat ID *</span>
                    <input
                      className={fieldClassName}
                      value={draft.telegramChatId}
                      onChange={(event) => patchDraft({ telegramChatId: event.target.value })}
                      placeholder="e.g. 123456789"
                    />
                  </label>
                ) : null}
              </div>
            </FormSection>
          ) : null}

          <FormSection title="Message">
            <div className="grid gap-4">
              <label className="block max-w-xl">
                <span className={labelClassName}>Template</span>
                <Combobox
                items={[
                  { value: "", label: "No template" },
                  ...templates.map((template) => ({
                    value: template.id,
                    label: `${template.name} (${getReminderChannelLabel(template.channel)})`,
                  })),
                ]}
                value={draft.templateId || null}
                onChange={(next) => patchDraft({ templateId: next || "" })}
                placeholder={
                  templatesQuery.isLoading ? "Loading templates…" : "Select a template"
                }
                  searchable
                  className={comboboxClassName}
                />
              </label>
              <label className="block">
                <span className={labelClassName}>Custom Message</span>
                <textarea
                  className={textareaClassName}
                  value={draft.customMessage}
                  onChange={(event) => patchDraft({ customMessage: event.target.value })}
                  placeholder="Optional message body"
                />
              </label>
            </div>
          </FormSection>

          <FormSection title="Status">
            <label className="flex items-center justify-between gap-4 rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 py-3">
              <div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white">Active</div>
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  Inactive reminders remain in the list but are not eligible to send.
                </p>
              </div>
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-slate-300 text-[#14B8A6] accent-[#14B8A6] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40"
                checked={draft.isActive}
                onChange={(event) => patchDraft({ isActive: event.target.checked })}
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
