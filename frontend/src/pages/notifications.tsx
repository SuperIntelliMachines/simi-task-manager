import { DashboardLayout, LoadingState, SectionCard } from "../components/design-system";
import {
  useDeleteNotification,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "../lib/api/hooks";
import type { InAppNotificationRecord } from "../lib/api/types";

function formatWhen(value: string): string {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function NotificationsPage() {
  const listQuery = useNotifications({ limit: 100 });
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();
  const remove = useDeleteNotification();

  const items = listQuery.data?.notifications ?? [];

  if (listQuery.isLoading) {
    return <LoadingState label="Loading notifications..." />;
  }

  return (
    <DashboardLayout>
      <SectionCard
        title="Notifications"
        eyebrow="Inbox"
        action={
          <button
            type="button"
            className="rounded-full border border-[#14B8A6]/30 bg-[#14B8A6]/10 px-3 py-1.5 text-xs font-medium text-[#14B8A6] disabled:opacity-50"
            disabled={markAll.isPending || items.every((n: InAppNotificationRecord) => n.status !== "UNREAD")}
            onClick={() => void markAll.mutateAsync()}
          >
            Mark all read
          </button>
        }
      >
        {items.length === 0 ? (
          <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
            You have no notifications.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200/80 dark:border-white/10">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200/80 bg-slate-50/80 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Message</th>
                  <th className="px-4 py-3">Entity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70 dark:divide-white/10">
                {items.map((item: InAppNotificationRecord) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 dark:hover:bg-white/5">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">{item.title}</td>
                    <td className="max-w-md px-4 py-3 text-slate-600 dark:text-slate-300">{item.message}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                      {item.entity_type}
                      <span className="text-slate-400"> #{item.entity_id}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          item.status === "UNREAD"
                            ? "bg-[#14B8A6]/15 text-[#14B8A6]"
                            : "bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-slate-300"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-500">{formatWhen(item.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {item.status === "UNREAD" ? (
                          <button
                            type="button"
                            className="text-xs font-medium text-[#14B8A6] hover:underline"
                            onClick={() => void markRead.mutateAsync(item.id)}
                          >
                            Mark read
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="text-xs font-medium text-rose-400 hover:underline"
                          onClick={() => void remove.mutateAsync(item.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </DashboardLayout>
  );
}
