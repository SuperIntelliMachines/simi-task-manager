import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { ReminderStatusBadge } from "../../components/reminder-management/ReminderStatusBadge";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { PlatformTable } from "../../components/platform/platform-table";
import {
  ActionMenu,
  EyeIcon,
  PauseIcon,
  PencilIcon,
  PlayIcon,
  TrashIcon,
} from "../../components/ui/ActionMenu";
import Combobox from "../../components/ui/Combobox";
import { Button } from "../../components/ui/button";
import { useToast } from "../../components/ui/toast";
import { resolveApiErrorMessage } from "../../lib/api/errors";
import { PERMISSIONS } from "../../lib/auth/permissions";
import {
  comboboxClassName,
  fieldClassName,
} from "../../lib/reminder-management/constants";
import { formatChannels, formatDate, formatDateTime } from "../../lib/reminder-management/format";
import { getRemindersBasePath, remindersPath } from "../../lib/reminder-management/paths";
import { REMINDER_CHANNEL_OPTIONS } from "../../lib/reminders/channels";
import {
  useDeletePersonalReminder,
  usePersonalReminders,
  useTogglePersonalReminder,
} from "../../lib/personal-reminders/hooks";
import type {
  PersonalReminder,
  PersonalReminderListFilters,
  PersonalReminderStatus,
} from "../../lib/personal-reminders/types";

const STATUS_FILTER_OPTIONS: Array<{ value: PersonalReminderStatus | "all"; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "PENDING", label: "Pending" },
  { value: "SENT", label: "Sent" },
  { value: "FAILED", label: "Failed" },
  { value: "CANCELLED", label: "Cancelled" },
];

const ACTIVE_FILTER_OPTIONS = [
  { value: "all", label: "All" },
  { value: "true", label: "Active" },
  { value: "false", label: "Inactive" },
];

function PersonalReminderFiltersBar({
  value,
  onChange,
}: {
  value: PersonalReminderListFilters;
  onChange: (next: PersonalReminderListFilters) => void;
}) {
  const channelItems = [
    { value: "all", label: "All channels" },
    ...REMINDER_CHANNEL_OPTIONS.map((option) => ({
      value: option.key,
      label: option.label,
    })),
  ];

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <label className="block">
        <span className="sr-only">Search</span>
        <input
          className={fieldClassName}
          placeholder="Search reminders…"
          value={value.search}
          onChange={(event) => onChange({ ...value, search: event.target.value, page: 0 })}
        />
      </label>
      <Combobox
        items={STATUS_FILTER_OPTIONS.map((option) => ({
          value: option.value,
          label: option.label,
        }))}
        value={value.status}
        onChange={(next) =>
          onChange({
            ...value,
            status: (next || "all") as PersonalReminderListFilters["status"],
            page: 0,
          })
        }
        placeholder="All statuses"
        searchable={false}
        className={comboboxClassName}
      />
      <Combobox
        items={channelItems}
        value={value.channel}
        onChange={(next) =>
          onChange({
            ...value,
            channel: (next || "all") as PersonalReminderListFilters["channel"],
            page: 0,
          })
        }
        placeholder="All channels"
        searchable={false}
        className={comboboxClassName}
      />
      <Combobox
        items={ACTIVE_FILTER_OPTIONS}
        value={value.isActive === "all" ? "all" : value.isActive ? "true" : "false"}
        onChange={(next) => {
          let isActive: PersonalReminderListFilters["isActive"] = "all";
          if (next === "true") isActive = true;
          else if (next === "false") isActive = false;
          onChange({ ...value, isActive, page: 0 });
        }}
        placeholder="Active"
        searchable={false}
        className={comboboxClassName}
      />
    </div>
  );
}

function needsDeliveryDetails(channels: string[]): boolean {
  return channels.some((channel) =>
    ["email", "sms", "whatsapp", "telegram"].includes(channel.toLowerCase())
  );
}

export function ReminderListPage() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const base = getRemindersBasePath(pathname);
  const { showToast } = useToast();
  const { hasPermission } = useWorkbench();

  const canView = hasPermission(PERMISSIONS.remindersView);
  const canCreate = hasPermission(PERMISSIONS.remindersCreate);
  const canUpdate = hasPermission(PERMISSIONS.remindersUpdate);
  const canDelete = hasPermission(PERMISSIONS.remindersDelete);

  const [filters, setFilters] = useState<PersonalReminderListFilters>({
    search: "",
    status: "all",
    channel: "all",
    isActive: "all",
    page: 0,
    pageSize: 20,
  });
  const [viewing, setViewing] = useState<PersonalReminder | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const listQuery = usePersonalReminders(filters);
  const toggleMutation = useTogglePersonalReminder();
  const deleteMutation = useDeletePersonalReminder();

  const page = listQuery.data;
  const rows = useMemo(() => page?.items ?? [], [page?.items]);
  const total = page?.total ?? 0;
  const pageSize = filters.pageSize;
  const pageCount = Math.max(1, Math.ceil(total / pageSize) || 1);
  const canPrev = filters.page > 0;
  const canNext = (filters.page + 1) * pageSize < total;

  async function handleToggle(reminder: PersonalReminder) {
    if (!canUpdate) {
      showToast("You do not have permission to update reminders.", "error");
      return;
    }
    try {
      await toggleMutation.mutateAsync({ id: reminder.id, isActive: !reminder.is_active });
      showToast(reminder.is_active ? "Reminder disabled." : "Reminder enabled.", "success");
    } catch (error) {
      showToast(resolveApiErrorMessage(error, "Failed to update reminder"), "error");
    }
  }

  async function handleDelete() {
    if (!deletingId) return;
    if (!canDelete) {
      showToast("You do not have permission to delete reminders.", "error");
      return;
    }
    try {
      await deleteMutation.mutateAsync(deletingId);
      setDeletingId(null);
      showToast("Reminder deleted.", "success");
    } catch (error) {
      showToast(resolveApiErrorMessage(error, "Failed to delete reminder"), "error");
    }
  }

  if (!canView) {
    return (
      <DashboardLayout>
        <SectionCard eyebrow="Reminder Management" title="Reminder List">
          <p className="text-sm text-slate-400">You do not have permission to view reminders.</p>
        </SectionCard>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <SectionCard
        eyebrow="Reminder Management"
        title="Reminder List"
        action={
          canCreate ? (
            <Button asChild>
              <Link to={remindersPath(base, "create")}>Create Reminder</Link>
            </Button>
          ) : undefined
        }
      >
        <div className="mb-6">
          <PersonalReminderFiltersBar value={filters} onChange={setFilters} />
        </div>

        {listQuery.isLoading ? (
          <LoadingState label="Loading reminders…" />
        ) : listQuery.isError ? (
          <p className="text-sm text-rose-300">
            {resolveApiErrorMessage(listQuery.error, "Failed to load reminders.")}
          </p>
        ) : (
          <>
            <PlatformTable
              emptyMessage="No reminders found. Create a reminder to get started."
              columns={[
                { key: "name", label: "Reminder Name", className: "min-w-[280px]" },
                { key: "scheduled", label: "Scheduled Date & Time" },
                { key: "channels", label: "Channels" },
                { key: "status", label: "Status" },
                { key: "active", label: "Active" },
                { key: "createdAt", label: "Created Date" },
                { key: "actions", label: "Actions", className: "w-16 text-right" },
              ]}
              rows={rows.map((reminder) => ({
                id: reminder.id,
                cells: [
                  <div key="name" className="min-w-[280px] max-w-[420px]">
                    <div className="font-medium text-slate-900 dark:text-white">{reminder.title}</div>
                  </div>,
                  <span key="scheduled" className="whitespace-nowrap text-xs">
                    {formatDateTime(reminder.scheduled_at)}
                  </span>,
                  formatChannels(reminder.channels),
                  <ReminderStatusBadge key="status" status={reminder.status} />,
                  reminder.is_active ? "Yes" : "No",
                  formatDate(reminder.created_at),
                  <div key="actions" className="flex justify-end">
                    <ActionMenu
                      items={[
                        {
                          id: "view",
                          label: "View",
                          icon: <EyeIcon />,
                          onSelect: () => setViewing(reminder),
                        },
                        ...(canUpdate
                          ? [
                              {
                                id: "edit",
                                label: "Edit",
                                icon: <PencilIcon />,
                                onSelect: () => navigate(remindersPath(base, `${reminder.id}/edit`)),
                              },
                              {
                                id: "toggle",
                                label: reminder.is_active ? "Disable" : "Enable",
                                icon: reminder.is_active ? <PauseIcon /> : <PlayIcon />,
                                onSelect: () => void handleToggle(reminder),
                              },
                            ]
                          : []),
                        ...(canDelete
                          ? [
                              {
                                id: "delete",
                                label: "Delete",
                                icon: <TrashIcon />,
                                tone: "danger" as const,
                                onSelect: () => setDeletingId(reminder.id),
                              },
                            ]
                          : []),
                      ]}
                    />
                  </div>,
                ],
              }))}
            />

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
              <span>
                {total === 0
                  ? "0 reminders"
                  : `Showing ${filters.page * pageSize + 1}–${Math.min((filters.page + 1) * pageSize, total)} of ${total}`}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  disabled={!canPrev || listQuery.isFetching}
                  onClick={() => setFilters((current) => ({ ...current, page: current.page - 1 }))}
                >
                  Previous
                </Button>
                <span className="px-2">
                  Page {filters.page + 1} / {pageCount}
                </span>
                <Button
                  variant="outline"
                  disabled={!canNext || listQuery.isFetching}
                  onClick={() => setFilters((current) => ({ ...current, page: current.page + 1 }))}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </SectionCard>

      <PlatformDialog
        open={Boolean(viewing)}
        onClose={() => setViewing(null)}
        title={viewing?.title ?? "Reminder"}
        description="Reminder details"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setViewing(null)}>
              Close
            </Button>
            {canUpdate ? (
              <Button
                onClick={() => {
                  const id = viewing?.id;
                  setViewing(null);
                  if (id) navigate(remindersPath(base, `${id}/edit`));
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
                <dt className="text-xs uppercase tracking-wide text-slate-500">Scheduled</dt>
                <dd>{formatDateTime(viewing.scheduled_at)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Status</dt>
                <dd>
                  <ReminderStatusBadge status={viewing.status} />
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Channels</dt>
                <dd>{formatChannels(viewing.channels)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Active</dt>
                <dd>{viewing.is_active ? "Yes" : "No"}</dd>
              </div>
              {needsDeliveryDetails(viewing.channels) ? (
                <>
                  {viewing.channels.includes("email") ? (
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-slate-500">Email</dt>
                      <dd>{viewing.email || "—"}</dd>
                    </div>
                  ) : null}
                  {viewing.channels.includes("sms") ? (
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-slate-500">Mobile</dt>
                      <dd>{viewing.mobile_number || "—"}</dd>
                    </div>
                  ) : null}
                  {viewing.channels.includes("whatsapp") ? (
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-slate-500">WhatsApp</dt>
                      <dd>{viewing.whatsapp_number || "—"}</dd>
                    </div>
                  ) : null}
                  {viewing.channels.includes("telegram") ? (
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-slate-500">Telegram</dt>
                      <dd>{viewing.telegram_chat_id || "—"}</dd>
                    </div>
                  ) : null}
                </>
              ) : null}
              <div className="sm:col-span-2">
                <dt className="text-xs uppercase tracking-wide text-slate-500">Message</dt>
                <dd>
                  {viewing.custom_message?.trim()
                    ? viewing.custom_message
                    : viewing.template_id
                      ? `Template: ${viewing.template_id}`
                      : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Created</dt>
                <dd>{formatDateTime(viewing.created_at)}</dd>
              </div>
            </dl>
          </div>
        ) : null}
      </PlatformDialog>

      <PlatformDialog
        open={Boolean(deletingId)}
        onClose={() => setDeletingId(null)}
        title="Delete reminder?"
        description="This permanently deletes the reminder."
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
