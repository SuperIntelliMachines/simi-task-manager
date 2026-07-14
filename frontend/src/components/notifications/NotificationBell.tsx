import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadNotificationCount,
} from "../../lib/api/hooks";
import type { InAppNotificationRecord } from "../../lib/api/types";

function formatWhen(value: string): string {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function notificationsPagePath(): string {
  const path = window.location.pathname || "";
  if (path.startsWith("/claims")) return "/claims/notifications";
  if (path.startsWith("/master")) return "/master/notifications";
  return "/app/notifications";
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const unreadQuery = useUnreadNotificationCount();
  const listQuery = useNotifications({ limit: 8 });
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  const unread = unreadQuery.data?.unread_count ?? 0;
  const items = listQuery.data?.notifications ?? [];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  async function handleItemClick(item: InAppNotificationRecord) {
    if (item.status === "UNREAD") {
      await markRead.mutateAsync(item.id);
    }
  }

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        aria-label="Notifications"
        className="gyantra-header-icon-btn relative"
        onClick={() => setOpen((v) => !v)}
      >
        🔔
        {unread > 0 ? (
          <span className="absolute -right-0.5 -top-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[#14B8A6] px-1 text-[10px] font-bold text-[#050816]">
            {unread > 99 ? "99+" : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 z-50 mt-2 w-[340px] overflow-hidden rounded-2xl border border-white/10 bg-black/85 shadow-xl backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <p className="text-sm font-semibold text-white">Notifications</p>
            <button
              type="button"
              className="text-xs font-medium text-[#14B8A6] hover:underline disabled:opacity-50"
              disabled={unread === 0 || markAll.isPending}
              onClick={() => void markAll.mutateAsync()}
            >
              Mark all read
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-slate-400">No notifications yet.</p>
            ) : (
              items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => void handleItemClick(item)}
                  className={`block w-full border-b border-white/5 px-4 py-3 text-left transition hover:bg-white/5 ${
                    item.status === "UNREAD" ? "bg-[#14B8A6]/5" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="truncate text-sm font-medium text-white">{item.title}</p>
                    {item.status === "UNREAD" ? (
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[#14B8A6]" />
                    ) : null}
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-400">{item.message}</p>
                  <p className="mt-1 text-[11px] text-slate-500">
                    {item.entity_type} · {formatWhen(item.created_at)}
                  </p>
                </button>
              ))
            )}
          </div>

          <div className="border-t border-white/10 px-4 py-2.5">
            <Link
              to={notificationsPagePath()}
              onClick={() => setOpen(false)}
              className="text-xs font-medium text-[#14B8A6] hover:underline"
            >
              View all notifications
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
