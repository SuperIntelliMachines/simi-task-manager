import { statusToneClass } from "../../lib/reminder-management/format";
import type { ReminderHistoryStatus, ReminderStatus } from "../../lib/reminder-management/types";

export function ReminderStatusBadge({
  status,
}: {
  status: ReminderStatus | ReminderHistoryStatus | string;
}) {
  const label = String(status || "—").replace(/_/g, " ");
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${statusToneClass(status)}`}
    >
      {label.toLowerCase()}
    </span>
  );
}
