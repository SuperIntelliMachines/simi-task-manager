import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { ReminderListFiltersBar } from "../../components/reminder-management/ReminderFilters";
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
import { Button } from "../../components/ui/button";
import { useToast } from "../../components/ui/toast";
import { resolveApiErrorMessage } from "../../lib/api/errors";
import { PERMISSIONS } from "../../lib/auth/permissions";
import {
  formatChannels,
  formatDate,
  formatDateTime,
  formatRecipients,
  formatSchedule,
  moduleLabel,
  triggerKindLabel,
} from "../../lib/reminder-management/format";
import {
  useDeleteManagedReminder,
  useManagedReminders,
  useToggleManagedReminder,
} from "../../lib/reminder-management/hooks";
import { getRemindersBasePath, remindersPath } from "../../lib/reminder-management/paths";
import type { ManagedReminder, ReminderListFilters } from "../../lib/reminder-management/types";

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

  const [filters, setFilters] = useState<ReminderListFilters>({
    search: "",
    module: "all",
    status: "all",
    channel: "all",
    page: 0,
    pageSize: 20,
  });
  const [viewing, setViewing] = useState<ManagedReminder | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const listQuery = useManagedReminders(filters);
  const toggleMutation = useToggleManagedReminder();
  const deleteMutation = useDeleteManagedReminder();

  const page = listQuery.data;
  const rows = useMemo(() => page?.items ?? [], [page?.items]);
  const total = page?.total ?? 0;
  const pageSize = filters.pageSize;
  const pageCount = Math.max(1, Math.ceil(total / pageSize) || 1);
  const canPrev = filters.page > 0;
  const canNext = (filters.page + 1) * pageSize < total;

  function updateFilters(next: ReminderListFilters) {
    const filterChanged =
      next.search !== filters.search ||
      next.module !== filters.module ||
      next.status !== filters.status ||
      next.channel !== filters.channel ||
      next.pageSize !== filters.pageSize;
    setFilters(filterChanged ? { ...next, page: 0 } : next);
  }

  async function handleToggle(reminder: ManagedReminder) {
    if (!canUpdate) {
      showToast("You do not have permission to update reminders.", "error");
      return;
    }
    try {
      await toggleMutation.mutateAsync({ id: reminder.id, enabled: !reminder.enabled });
      showToast(reminder.enabled ? "Reminder disabled." : "Reminder enabled.", "success");
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
          <ReminderListFiltersBar value={filters} onChange={updateFilters} />
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
                { key: "name", label: "Reminder Name" },
                { key: "module", label: "Module" },
                { key: "trigger", label: "Trigger" },
                { key: "schedule", label: "Schedule" },
                { key: "recipients", label: "Recipients" },
                { key: "channels", label: "Channels" },
                { key: "status", label: "Status" },
                { key: "next", label: "Next Trigger" },
                { key: "createdBy", label: "Created By" },
                { key: "createdAt", label: "Created Date" },
                { key: "actions", label: "Actions", className: "w-16 text-right" },
              ]}
              rows={rows.map((reminder) => ({
                id: reminder.id,
                cells: [
                  <div key="name" className="min-w-[160px]">
                    <div className="font-medium text-slate-900 dark:text-white">{reminder.name}</div>
                  </div>,
                  moduleLabel(reminder.module),
                  <div key="trigger" className="min-w-[120px]">
                    <div>{reminder.triggerLabel || reminder.triggerKey}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {triggerKindLabel(reminder.triggerKind)}
                    </div>
                  </div>,
                  <span key="schedule" className="whitespace-nowrap text-xs">
                    {formatSchedule(reminder)}
                  </span>,
                  formatRecipients(reminder),
                  formatChannels(reminder.channels),
                  <ReminderStatusBadge key="status" status={reminder.status} />,
                  formatDateTime(reminder.nextTriggerAt),
                  reminder.createdBy,
                  formatDate(reminder.createdAt),
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
                                label: reminder.enabled ? "Disable" : "Enable",
                                icon: reminder.enabled ? <PauseIcon /> : <PlayIcon />,
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
        title={viewing?.name ?? "Reminder"}
        description="Reminder definition overview"
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
            <p>{viewing.description || "No description."}</p>
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Module</dt>
                <dd>{moduleLabel(viewing.module)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Trigger</dt>
                <dd>
                  {viewing.triggerLabel || viewing.triggerKey} ({triggerKindLabel(viewing.triggerKind)})
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Schedule</dt>
                <dd>{formatSchedule(viewing)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-500">Channels</dt>
                <dd>{formatChannels(viewing.channels)}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs uppercase tracking-wide text-slate-500">Recipients</dt>
                <dd>{viewing.recipients.map((item) => item.label).join(", ") || "—"}</dd>
              </div>
            </dl>
          </div>
        ) : null}
      </PlatformDialog>

      <PlatformDialog
        open={Boolean(deletingId)}
        onClose={() => setDeletingId(null)}
        title="Delete reminder?"
        description="This permanently deletes the reminder definition."
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
        <p className="text-sm text-slate-600 dark:text-slate-300">
          This action cannot be undone.
        </p>
      </PlatformDialog>
    </DashboardLayout>
  );
}
