import { useEffect, useMemo, useState } from "react";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { PlatformTable } from "../../components/platform/platform-table";
import {
  ActionMenu,
  EyeIcon,
  PencilIcon,
  TrashIcon,
} from "../../components/ui/ActionMenu";
import Combobox from "../../components/ui/Combobox";
import { Button } from "../../components/ui/button";
import { useToast } from "../../components/ui/toast";
import { resolveApiErrorMessage } from "../../lib/api/errors";
import { PERMISSIONS } from "../../lib/auth/permissions";
import {
  REMINDER_TEMPLATE_CHANNEL_OPTIONS,
  emptyReminderTemplateDraft,
  formatApprovalStatus,
  recordToDraft,
  validateReminderTemplateDraft,
} from "../../lib/reminder-templates/api";
import {
  useCreateReminderTemplate,
  useDeleteReminderTemplate,
  useReminderTemplates,
  useUpdateReminderTemplate,
} from "../../lib/reminder-templates/hooks";
import type {
  ReminderTemplateDraft,
  ReminderTemplateListFilters,
  ReminderTemplateRecord,
} from "../../lib/reminder-templates/types";
import {
  comboboxClassName,
  fieldClassName,
  labelClassName,
  textareaClassName,
} from "../../lib/reminder-management/constants";
import { formatDate } from "../../lib/reminder-management/format";
import { getReminderChannelLabel } from "../../lib/reminders/channels";

function WhatsAppApprovalBadge({ status }: { status: string | null }) {
  if (!status) return null;
  const label = formatApprovalStatus(status);
  const tone =
    status === "approved"
      ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
      : status === "rejected"
        ? "bg-rose-500/15 text-rose-300 ring-rose-500/30"
        : status === "pending_approval"
          ? "bg-amber-500/15 text-amber-200 ring-amber-500/30"
          : "bg-slate-500/15 text-slate-300 ring-slate-500/30";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${tone}`}
    >
      {label}
    </span>
  );
}

function TemplateFormFields({
  draft,
  onChange,
}: {
  draft: ReminderTemplateDraft;
  onChange: (patch: Partial<ReminderTemplateDraft>) => void;
}) {
  const channel = draft.channel.toLowerCase();
  const isWhatsApp = channel === "whatsapp";

  return (
    <div className="space-y-4">
      <label className="block">
        <span className={labelClassName}>Template Name *</span>
        <input
          className={fieldClassName}
          value={draft.name}
          onChange={(event) => onChange({ name: event.target.value })}
          placeholder="e.g. Policy renewal notice"
        />
      </label>

      <label className="block">
        <span className={labelClassName}>Channel *</span>
        <Combobox
          items={REMINDER_TEMPLATE_CHANNEL_OPTIONS.map((option) => ({
            value: option.value,
            label: option.label,
          }))}
          value={draft.channel}
          onChange={(next) => onChange({ channel: next || "email" })}
          placeholder="Select channel"
          searchable={false}
          className={comboboxClassName}
        />
      </label>

      {isWhatsApp ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          WhatsApp templates require Meta approval before they can be used.
        </div>
      ) : null}

      {channel === "email" ? (
        <label className="block">
          <span className={labelClassName}>Subject *</span>
          <input
            className={fieldClassName}
            value={draft.subject}
            onChange={(event) => onChange({ subject: event.target.value })}
            placeholder="Email subject line"
          />
        </label>
      ) : null}

      {channel === "in_app" ? (
        <label className="block">
          <span className={labelClassName}>Title *</span>
          <input
            className={fieldClassName}
            value={draft.title}
            onChange={(event) => onChange({ title: event.target.value })}
            placeholder="In-app notification title"
          />
        </label>
      ) : null}

      {isWhatsApp ? (
        <label className="block">
          <span className={labelClassName}>WhatsApp Template Name *</span>
          <input
            className={fieldClassName}
            value={draft.whatsappTemplateName}
            onChange={(event) => onChange({ whatsappTemplateName: event.target.value })}
            placeholder="Meta template name (future submission)"
          />
        </label>
      ) : null}

      <label className="block">
        <span className={labelClassName}>Template Body *</span>
        <textarea
          className={textareaClassName}
          value={draft.body}
          onChange={(event) => onChange({ body: event.target.value })}
          placeholder="Message body with optional placeholders"
        />
      </label>

      {isWhatsApp ? (
        <label className="block">
          <span className={labelClassName}>Variables (optional)</span>
          <input
            className={fieldClassName}
            value={draft.variablesText}
            onChange={(event) => onChange({ variablesText: event.target.value })}
            placeholder="customer_name, due_date"
          />
          <p className="mt-1 text-xs text-slate-500">Comma-separated variable names.</p>
        </label>
      ) : null}

      <label className="flex items-center justify-between gap-4 rounded-xl border border-slate-300/90 bg-white/90 dark:border-white/10 dark:bg-slate-950/40 px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-slate-900 dark:text-white">Active</div>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Inactive templates are hidden from reminder creation.
          </p>
        </div>
        <input
          type="checkbox"
          className="h-5 w-5 rounded border-slate-300 text-[#14B8A6] accent-[#14B8A6]"
          checked={draft.isActive}
          onChange={(event) => onChange({ isActive: event.target.checked })}
        />
      </label>
    </div>
  );
}

export function ReminderTemplatesPage() {
  const { showToast } = useToast();
  const { hasPermission } = useWorkbench();
  // Templates lives under Reminder Management nav (reminders:view). Allow either
  // templates:* or reminders:* so Create is not hidden for typical reminder users.
  const canView =
    hasPermission(PERMISSIONS.templatesView) || hasPermission(PERMISSIONS.remindersView);
  const canCreate =
    hasPermission(PERMISSIONS.templatesCreate) ||
    hasPermission(PERMISSIONS.remindersCreate);
  const canUpdate =
    hasPermission(PERMISSIONS.templatesUpdate) ||
    hasPermission(PERMISSIONS.remindersUpdate);

  const [filters, setFilters] = useState<ReminderTemplateListFilters>({
    search: "",
    channel: "all",
    isActive: "all",
  });
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ReminderTemplateDraft>(() => emptyReminderTemplateDraft());
  const [viewing, setViewing] = useState<ReminderTemplateRecord | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const listQuery = useReminderTemplates(filters);
  const createMutation = useCreateReminderTemplate();
  const updateMutation = useUpdateReminderTemplate();
  const deleteMutation = useDeleteReminderTemplate();

  const rows = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items]);

  useEffect(() => {
    if (draft.channel === "whatsapp" && !draft.whatsappTemplateName && draft.name) {
      setDraft((current) => ({ ...current, whatsappTemplateName: current.name }));
    }
  }, [draft.channel, draft.name, draft.whatsappTemplateName]);

  function openCreate() {
    if (!canCreate) {
      showToast("You do not have permission to create templates.", "error");
      return;
    }
    setEditingId(null);
    setDraft(emptyReminderTemplateDraft());
    setEditorOpen(true);
  }

  function openEdit(record: ReminderTemplateRecord) {
    setEditingId(record.id);
    setDraft(recordToDraft(record));
    setEditorOpen(true);
  }

  async function handleSave() {
    const error = validateReminderTemplateDraft(draft);
    if (error) {
      showToast(error, "error");
      return;
    }
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, draft });
        showToast("Template updated.", "success");
      } else {
        await createMutation.mutateAsync(draft);
        showToast("Template created.", "success");
      }
      setEditorOpen(false);
    } catch (error) {
      showToast(resolveApiErrorMessage(error, "Failed to save template"), "error");
    }
  }

  async function handleDelete() {
    if (!deletingId) return;
    try {
      await deleteMutation.mutateAsync(deletingId);
      setDeletingId(null);
      showToast("Template deleted.", "success");
    } catch (error) {
      showToast(resolveApiErrorMessage(error, "Failed to delete template"), "error");
    }
  }

  if (!canView) {
    return (
      <DashboardLayout>
        <SectionCard eyebrow="Reminder Management" title="Templates">
          <p className="text-sm text-slate-400">You do not have permission to view templates.</p>
        </SectionCard>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <SectionCard
        eyebrow="Reminder Management"
        title="Templates"
        action={
          <Button onClick={openCreate} disabled={!canCreate}>
            + Create Template
          </Button>
        }
      >
        <div className="mb-6 grid gap-3 md:grid-cols-3">
          <input
            className={fieldClassName}
            placeholder="Search…"
            value={filters.search}
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
          />
          <Combobox
            items={[
              { value: "all", label: "All channels" },
              ...REMINDER_TEMPLATE_CHANNEL_OPTIONS.map((option) => ({
                value: option.value,
                label: option.label,
              })),
            ]}
            value={filters.channel}
            onChange={(next) =>
              setFilters((current) => ({ ...current, channel: next || "all" }))
            }
            placeholder="Channel Filter"
            searchable={false}
            className={comboboxClassName}
          />
          <Combobox
            items={[
              { value: "all", label: "All statuses" },
              { value: "true", label: "Active" },
              { value: "false", label: "Inactive" },
            ]}
            value={filters.isActive === "all" ? "all" : filters.isActive ? "true" : "false"}
            onChange={(next) => {
              let isActive: ReminderTemplateListFilters["isActive"] = "all";
              if (next === "true") isActive = true;
              else if (next === "false") isActive = false;
              setFilters((current) => ({ ...current, isActive }));
            }}
            placeholder="Status Filter"
            searchable={false}
            className={comboboxClassName}
          />
        </div>

        {listQuery.isLoading ? (
          <LoadingState label="Loading templates…" />
        ) : listQuery.isError ? (
          <p className="text-sm text-rose-300">
            {resolveApiErrorMessage(listQuery.error, "Failed to load templates.")}
          </p>
        ) : rows.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300/80 bg-white/60 px-6 py-12 text-center dark:border-white/10 dark:bg-slate-950/30">
            <p className="text-base font-semibold text-slate-900 dark:text-white">No templates yet.</p>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Create your first reminder template.
            </p>
            <Button className="mt-6" onClick={openCreate} disabled={!canCreate}>
              Create Template
            </Button>
          </div>
        ) : (
          <PlatformTable
            emptyMessage="No templates yet."
            columns={[
              { key: "name", label: "Template Name" },
              { key: "channel", label: "Channel" },
              { key: "status", label: "Status" },
              { key: "created", label: "Created Date" },
              { key: "actions", label: "Actions", className: "w-16 text-right" },
            ]}
            rows={rows.map((template) => ({
              id: template.id,
              cells: [
                template.name,
                getReminderChannelLabel(template.channel),
                template.channel === "whatsapp" ? (
                  <WhatsAppApprovalBadge key="status" status={template.approval_status} />
                ) : (
                  <span
                    key="status"
                    className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${
                      template.is_active
                        ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30"
                        : "bg-slate-500/15 text-slate-300 ring-slate-500/30"
                    }`}
                  >
                    {template.is_active ? "Active" : "Inactive"}
                  </span>
                ),
                formatDate(template.created_at),
                <div key="actions" className="flex justify-end">
                  <ActionMenu
                    items={[
                      {
                        id: "view",
                        label: "View",
                        icon: <EyeIcon />,
                        onSelect: () => setViewing(template),
                      },
                      ...(canUpdate
                        ? [
                            {
                              id: "edit",
                              label: "Edit",
                              icon: <PencilIcon />,
                              onSelect: () => openEdit(template),
                            },
                            {
                              id: "delete",
                              label: "Delete",
                              icon: <TrashIcon />,
                              tone: "danger" as const,
                              onSelect: () => setDeletingId(template.id),
                            },
                          ]
                        : []),
                    ]}
                  />
                </div>,
              ],
            }))}
          />
        )}
      </SectionCard>

      <PlatformDialog
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        title={editingId ? "Edit Template" : "Create Template"}
        description="Configure a reminder template for your selected channel."
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setEditorOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleSave()}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending ? "Saving…" : "Save Template"}
            </Button>
          </>
        }
      >
        <TemplateFormFields draft={draft} onChange={(patch) => setDraft((current) => ({ ...current, ...patch }))} />
      </PlatformDialog>

      <PlatformDialog
        open={Boolean(viewing)}
        onClose={() => setViewing(null)}
        title={viewing?.name ?? "Template"}
        description={viewing ? getReminderChannelLabel(viewing.channel) : undefined}
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setViewing(null)}>
              Close
            </Button>
            {canUpdate && viewing ? (
              <Button
                onClick={() => {
                  openEdit(viewing);
                  setViewing(null);
                }}
              >
                Edit
              </Button>
            ) : null}
          </>
        }
      >
        {viewing ? (
          <div className="space-y-3 text-sm text-slate-700 dark:text-slate-300">
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Channel</dt>
                <dd>{getReminderChannelLabel(viewing.channel)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Active</dt>
                <dd>{viewing.is_active ? "Yes" : "No"}</dd>
              </div>
              {viewing.channel === "email" ? (
                <div className="sm:col-span-2">
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Subject</dt>
                  <dd>{viewing.subject || "—"}</dd>
                </div>
              ) : null}
              {viewing.channel === "in_app" ? (
                <div className="sm:col-span-2">
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Title</dt>
                  <dd>{viewing.title || "—"}</dd>
                </div>
              ) : null}
              {viewing.channel === "whatsapp" ? (
                <>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-500">Status</dt>
                    <dd>
                      <WhatsAppApprovalBadge status={viewing.approval_status} />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-500">WhatsApp Name</dt>
                    <dd>{viewing.whatsapp_template_name || "—"}</dd>
                  </div>
                </>
              ) : null}
              <div className="sm:col-span-2">
                <dt className="text-xs uppercase tracking-wide text-slate-500">Variables</dt>
                <dd>{viewing.variables?.length ? viewing.variables.join(", ") : "—"}</dd>
              </div>
            </dl>
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">Body</div>
              <pre className="mt-2 whitespace-pre-wrap rounded-xl border border-white/10 bg-slate-950/40 p-4 text-slate-200">
                {viewing.body}
              </pre>
            </div>
          </div>
        ) : null}
      </PlatformDialog>

      <PlatformDialog
        open={Boolean(deletingId)}
        onClose={() => setDeletingId(null)}
        title="Delete template?"
        description="This permanently deletes the template."
        footer={
          <>
            <Button variant="outline" onClick={() => setDeletingId(null)}>
              Cancel
            </Button>
            <Button onClick={() => void handleDelete()} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600 dark:text-slate-300">This action cannot be undone.</p>
      </PlatformDialog>
    </DashboardLayout>
  );
}
