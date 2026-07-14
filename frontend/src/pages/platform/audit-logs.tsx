import { useMemo, useState } from "react";

import { ADMIN_CONSOLE_EYEBROW } from "../../lib/auth/role-labels";
import { DashboardLayout, LoadingState, SectionCard } from "../../components/design-system";
import { PlatformTable } from "../../components/platform/platform-table";
import { usePlatformAuditLogs } from "../../lib/platform/hooks";

export function PlatformAuditLogsPage() {
  const [sourceFilter, setSourceFilter] = useState<"all" | "login_audit" | "audit_event">("all");
  const [search, setSearch] = useState("");
  const auditQuery = usePlatformAuditLogs(200);

  const filtered = useMemo(() => {
    let rows = auditQuery.data ?? [];
    if (sourceFilter !== "all") rows = rows.filter((log) => log.source === sourceFilter);
    const q = search.trim().toLowerCase();
    if (q) {
      rows = rows.filter((log) =>
        (log.email ?? "").toLowerCase().includes(q) ||
        (log.event_type ?? "").toLowerCase().includes(q) ||
        (log.failure_reason ?? "").toLowerCase().includes(q),
      );
    }
    return rows;
  }, [auditQuery.data, sourceFilter, search]);

  if (auditQuery.isLoading) return <LoadingState label="Loading audit logs..." />;

  return (
    <DashboardLayout>
      <SectionCard title="Audit Logs" eyebrow={ADMIN_CONSOLE_EYEBROW}>
        <div className="mb-4 flex flex-col gap-3 md:flex-row">
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search audit logs..." className="login-input w-full max-w-md px-4 py-2 text-sm" />
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value as typeof sourceFilter)} className="login-input w-full max-w-xs px-4 py-2 text-sm">
            <option value="all">All sources</option>
            <option value="login_audit">Login audit</option>
            <option value="audit_event">System events</option>
          </select>
        </div>

        <PlatformTable
          columns={[
            { key: "time", label: "Timestamp" },
            { key: "source", label: "Source" },
            { key: "detail", label: "Details" },
            { key: "status", label: "Status" },
          ]}
          rows={filtered.map((log) => ({
            id: `${log.source}-${log.id}`,
            cells: [
              log.created_at ? new Date(log.created_at).toLocaleString() : "—",
              log.source === "login_audit" ? "Login" : "Event",
              log.source === "login_audit" ? (
                <div>
                  <div className="font-medium">{log.email}</div>
                  <div className="text-xs text-slate-500">{log.ip_address || "No IP"}</div>
                </div>
              ) : (
                <div>
                  <div className="font-medium">{log.event_type}</div>
                  <div className="text-xs text-slate-500">{log.entity_type} {log.entity_id}</div>
                </div>
              ),
              log.source === "login_audit" ? (
                <span className={`rounded-full px-2 py-1 text-xs font-medium ${log.success ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" : "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300"}`}>
                  {log.success ? "Success" : log.failure_reason || "Failed"}
                </span>
              ) : (
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium dark:bg-white/10">Recorded</span>
              ),
            ],
          }))}
        />
      </SectionCard>
    </DashboardLayout>
  );
}
