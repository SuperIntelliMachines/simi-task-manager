import { useNavigate } from "react-router-dom";

import { DashboardLayout, HeroBanner, HeroBadge, KpiGrid, KpiCard, LoadingState, SectionCard } from "../../components/design-system";
import { ADMIN_CONSOLE_EYEBROW, ADMIN_CONSOLE_NAME, ADMIN_CONSOLE_TITLE } from "../../lib/auth/role-labels";
import { usePlatformStats } from "../../lib/platform/hooks";
import { Sparkles } from "../../components/insurance/icons";

export function PlatformDashboardPage() {
  const navigate = useNavigate();
  const statsQuery = usePlatformStats();

  if (statsQuery.isLoading) return <LoadingState label={`Loading ${ADMIN_CONSOLE_NAME.toLowerCase()}...`} />;

  const stats = statsQuery.data ?? {
    total_organizations: 0,
    total_users: 0,
    active_organizations: 0,
    total_agents: 0,
    total_tasks: 0,
    system_status: "unknown",
  };

  return (
    <DashboardLayout>
      <HeroBanner
        userName="Administrator"
        badge={<HeroBadge icon={<Sparkles className="h-3.5 w-3.5 text-[#8B5CF6]" />} label={ADMIN_CONSOLE_NAME} />}
        subtitle="Monitor organizations, users, agents, and system health across SIMI."
      />

      <KpiGrid title={`${ADMIN_CONSOLE_NAME} Overview`} columns="3">
        <KpiCard title="Total Organizations" count={stats.total_organizations} accent="purple" delay={0.05} icon={<span className="text-lg">🏢</span>} onClick={() => navigate("/master/organizations")} />
        <KpiCard title="Total Users" count={stats.total_users} accent="teal" delay={0.1} icon={<span className="text-lg">👥</span>} onClick={() => navigate("/master/users")} />
        <KpiCard title="Active Organizations" count={stats.active_organizations} accent="blue" delay={0.15} icon={<span className="text-lg">✓</span>} />
        <KpiCard title="Total AI Agents" count={stats.total_agents} accent="cyan" delay={0.2} icon={<span className="text-lg">✦</span>} />
        <KpiCard title="Total Tasks" count={stats.total_tasks} accent="amber" delay={0.25} icon={<span className="text-lg">☑</span>} />
        <KpiCard title="System Status" count={stats.system_status === "healthy" ? 100 : 0} accent="teal" delay={0.3} icon={<span className="text-lg">●</span>} />
      </KpiGrid>

      <SectionCard title="Administration Shortcuts" eyebrow={ADMIN_CONSOLE_EYEBROW}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[
            { label: "Manage Organizations", to: "/master/organizations" },
            { label: "Manage Users", to: "/master/users" },
            { label: "Role Configuration", to: "/master/roles" },
            { label: "Permissions", to: "/master/permissions" },
            { label: "Audit Logs", to: "/master/audit" },
            { label: "Console Settings", to: "/master/settings" },
          ].map((item) => (
            <button
              key={item.to}
              type="button"
              onClick={() => navigate(item.to)}
              className="rounded-2xl border border-slate-200/80 bg-white/55 px-4 py-4 text-left text-sm font-medium text-slate-800 transition hover:-translate-y-0.5 hover:border-[#14B8A6]/30 dark:border-white/10 dark:bg-slate-950/70 dark:text-slate-100"
            >
              {item.label}
            </button>
          ))}
        </div>
      </SectionCard>
    </DashboardLayout>
  );
}
