import { useState } from "react";

import { ReminderHistoryFiltersBar } from "../../components/reminder-management/ReminderFilters";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformTable } from "../../components/platform/platform-table";
import { useReminderHistory } from "../../lib/reminder-management/hooks";
import type { ReminderHistoryFilters } from "../../lib/reminder-management/types";

export function ReminderHistoryPage() {
  const [filters, setFilters] = useState<ReminderHistoryFilters>({
    module: "all",
    status: "all",
    channel: "all",
    dateFrom: "",
    dateTo: "",
  });

  const historyQuery = useReminderHistory(filters);
  const rows = historyQuery.data ?? [];

  return (
    <DashboardLayout>
      <SectionCard eyebrow="Reminder Management" title="Reminder History">
        <p className="mb-4 text-sm text-slate-400">
          Execution history for general reminder definitions is not stored in this phase. This view
          will connect when delivery tracking is available.
        </p>
        <div className="mb-6">
          <ReminderHistoryFiltersBar value={filters} onChange={setFilters} />
        </div>

        {historyQuery.isLoading ? (
          <LoadingState label="Loading history…" />
        ) : (
          <PlatformTable
            emptyMessage="No reminder execution history available yet."
            columns={[
              { key: "reminder", label: "Reminder" },
              { key: "trigger", label: "Trigger Time" },
              { key: "recipient", label: "Recipient" },
              { key: "channel", label: "Channel" },
              { key: "status", label: "Status" },
              { key: "sent", label: "Sent Time" },
              { key: "error", label: "Error" },
            ]}
            rows={rows.map((entry) => ({
              id: entry.id,
              cells: [
                entry.reminderName,
                entry.triggerTime,
                entry.recipient,
                entry.channel,
                entry.status,
                entry.sentTime ?? "—",
                entry.error ?? "—",
              ],
            }))}
          />
        )}
      </SectionCard>
    </DashboardLayout>
  );
}
