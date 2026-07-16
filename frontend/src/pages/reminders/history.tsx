import { useState, type ReactNode } from "react";

import { useWorkbench } from "../../app/providers/workbench-provider";
import { ReminderHistoryFiltersBar } from "../../components/reminder-management/ReminderFilters";
import { ReminderStatusBadge } from "../../components/reminder-management/ReminderStatusBadge";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformDialog } from "../../components/platform/platform-dialog";
import { PlatformTable } from "../../components/platform/platform-table";
import { ActionMenu, EyeIcon } from "../../components/ui/ActionMenu";
import { Button } from "../../components/ui/button";
import { resolveApiErrorMessage } from "../../lib/api/errors";
import { PERMISSIONS } from "../../lib/auth/permissions";
import { formatDateTime } from "../../lib/reminder-management/format";
import type { ReminderHistoryFilters } from "../../lib/reminder-management/types";
import {
  useReminderHistory,
  useReminderHistoryDetail,
} from "../../lib/reminder-history/hooks";
import { getReminderChannelLabel } from "../../lib/reminders/channels";

const DEFAULT_PAGE_SIZE = 50;

function DetailField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 break-words text-slate-700 dark:text-slate-200">{children}</dd>
    </div>
  );
}

export function ReminderHistoryPage() {
  const { hasPermission } = useWorkbench();
  const canView = hasPermission(PERMISSIONS.remindersView);

  const [filters, setFilters] = useState<ReminderHistoryFilters>({
    module: "all",
    status: "all",
    channel: "all",
    dateFrom: "",
    dateTo: "",
    search: "",
    page: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  });
  const [viewingId, setViewingId] = useState<string | null>(null);

  const historyQuery = useReminderHistory(filters);
  const detailQuery = useReminderHistoryDetail(viewingId ?? undefined);

  const rows = historyQuery.data?.items ?? [];
  const total = historyQuery.data?.total ?? 0;
  const pageSize = filters.pageSize;
  const pageCount = Math.max(1, Math.ceil(total / pageSize) || 1);
  const canPrev = filters.page > 0;
  const canNext = filters.page + 1 < pageCount;

  if (!canView) {
    return (
      <DashboardLayout>
        <SectionCard eyebrow="Reminder Management" title="Reminder History">
          <p className="text-sm text-slate-400">You do not have permission to view reminder history.</p>
        </SectionCard>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <SectionCard eyebrow="Reminder Management" title="Reminder History">
        <p className="mb-4 text-sm text-slate-400">
          Delivery outcomes for personal reminders across channels.
        </p>
        <div className="mb-6">
          <ReminderHistoryFiltersBar value={filters} onChange={setFilters} />
        </div>

        {historyQuery.isLoading ? (
          <LoadingState label="Loading history…" />
        ) : historyQuery.isError ? (
          <p className="text-sm text-rose-300">
            {resolveApiErrorMessage(historyQuery.error, "Failed to load reminder history.")}
          </p>
        ) : (
          <>
            <PlatformTable
              emptyMessage="No reminder execution history found."
              columns={[
                { key: "title", label: "Reminder Title" },
                { key: "channel", label: "Channel" },
                { key: "recipient", label: "Recipient" },
                { key: "status", label: "Status" },
                { key: "executed", label: "Executed At" },
                { key: "provider", label: "Provider Message ID" },
                { key: "error", label: "Error Message" },
                { key: "actions", label: "Actions", className: "w-16 text-right" },
              ]}
              rows={rows.map((entry) => {
                const failed = String(entry.status).toUpperCase() === "FAILED";
                return {
                  id: entry.id,
                  cells: [
                    <button
                      key="title"
                      type="button"
                      className="min-w-[140px] text-left font-medium text-slate-900 hover:underline dark:text-white"
                      onClick={() => setViewingId(entry.id)}
                    >
                      {entry.reminder_title}
                    </button>,
                    getReminderChannelLabel(entry.channel),
                    <span key="recipient" className="max-w-[180px] truncate">
                      {entry.recipient || "—"}
                    </span>,
                    <ReminderStatusBadge key="status" status={entry.status} />,
                    <span key="executed" className="whitespace-nowrap text-xs">
                      {formatDateTime(entry.executed_at)}
                    </span>,
                    <span key="provider" className="max-w-[140px] truncate text-xs text-slate-500">
                      {entry.provider_message_id || "—"}
                    </span>,
                    <span
                      key="error"
                      className={`max-w-[200px] truncate text-xs ${failed ? "text-rose-300" : "text-slate-500"}`}
                    >
                      {failed ? entry.error_message || "—" : "—"}
                    </span>,
                    <div key="actions" className="flex justify-end">
                      <ActionMenu
                        items={[
                          {
                            id: "view",
                            label: "View",
                            icon: <EyeIcon />,
                            onSelect: () => setViewingId(entry.id),
                          },
                        ]}
                      />
                    </div>,
                  ],
                };
              })}
            />

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
              <span>
                {total === 0
                  ? "0 results"
                  : `Showing ${filters.page * pageSize + 1}–${Math.min((filters.page + 1) * pageSize, total)} of ${total}`}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  disabled={!canPrev || historyQuery.isFetching}
                  onClick={() => setFilters((current) => ({ ...current, page: current.page - 1 }))}
                >
                  Previous
                </Button>
                <span className="px-2">
                  Page {filters.page + 1} / {pageCount}
                </span>
                <Button
                  variant="outline"
                  disabled={!canNext || historyQuery.isFetching}
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
        open={Boolean(viewingId)}
        onClose={() => setViewingId(null)}
        title={detailQuery.data?.reminder_title ?? "Reminder execution"}
        description="Execution details"
        size="lg"
        footer={
          <Button variant="outline" onClick={() => setViewingId(null)}>
            Close
          </Button>
        }
      >
        {detailQuery.isLoading ? (
          <LoadingState label="Loading details…" />
        ) : detailQuery.isError ? (
          <p className="text-sm text-rose-300">
            {resolveApiErrorMessage(detailQuery.error, "Failed to load execution details.")}
          </p>
        ) : detailQuery.data ? (
          <dl className="grid gap-3 sm:grid-cols-2">
            <DetailField label="Reminder">
              {detailQuery.data.reminder?.title ?? detailQuery.data.reminder_title}
            </DetailField>
            <DetailField label="Template">
              {detailQuery.data.template?.name ?? "—"}
            </DetailField>
            <DetailField label="Recipient">{detailQuery.data.recipient || "—"}</DetailField>
            <DetailField label="Channel">
              {getReminderChannelLabel(detailQuery.data.channel)}
            </DetailField>
            <DetailField label="Status">
              <ReminderStatusBadge status={detailQuery.data.status} />
            </DetailField>
            <DetailField label="Executed At">
              {formatDateTime(detailQuery.data.executed_at)}
            </DetailField>
            <DetailField label="Provider Message ID">
              {detailQuery.data.provider_message_id || "—"}
            </DetailField>
            <DetailField label="Error Message">
              {detailQuery.data.error_message || "—"}
            </DetailField>
            <DetailField label="Scheduled Time">
              {formatDateTime(detailQuery.data.reminder?.scheduled_at)}
            </DetailField>
            <DetailField label="Created By">{detailQuery.data.created_by}</DetailField>
          </dl>
        ) : null}
      </PlatformDialog>
    </DashboardLayout>
  );
}
