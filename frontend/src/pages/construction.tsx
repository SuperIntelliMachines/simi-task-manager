import { useConstructionDashboard } from "../lib/api/hooks";
import { useWorkbench } from "../app/providers/workbench-provider";
import {
  DashboardLayout,
  HeroBadge,
  HeroBanner,
  LoadingState,
  SectionCard,
} from "../components/design-system";
import { Sparkles } from "../components/insurance/icons";

export function ConstructionPage() {
  const { currentUserName } = useWorkbench();
  const dashboardQuery = useConstructionDashboard();

  if (!dashboardQuery.data) {
    return (
      <DashboardLayout>
        <LoadingState label="Loading construction dashboard..." />
      </DashboardLayout>
    );
  }

  const data = dashboardQuery.data;

  return (
    <DashboardLayout>
      <HeroBanner
        userName={currentUserName}
        badge={
          <HeroBadge
            icon={<Sparkles className="h-3.5 w-3.5 text-[#8B5CF6]" />}
            label="Construction Operations"
          />
        }
        subtitle="Track site progress, worker load, and delivery risk in one place."
      />

      <div className="grid gap-6 xl:grid-cols-3">
        <SectionCard title="Risk Radar" eyebrow="Overdue + Blocked" delay={0.05}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-2xl border border-white/10 bg-white/50 p-4 dark:bg-slate-950/40">
              <p className="text-sm text-slate-600 dark:text-slate-400">Overdue tasks</p>
              <p className="text-3xl font-semibold text-slate-900 dark:text-white">{data.overdueTasks}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/50 p-4 dark:bg-slate-950/40">
              <p className="text-sm text-slate-600 dark:text-slate-400">Blocked tasks</p>
              <p className="text-3xl font-semibold text-slate-900 dark:text-white">{data.blockedTasks}</p>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Site Progress" eyebrow="Completion" delay={0.1}>
          <div className="space-y-3">
            {data.siteProgress.map((site) => (
              <div key={site.site}>
                <div className="flex justify-between text-sm text-slate-700 dark:text-slate-300">
                  <span>{site.site}</span>
                  <span>{site.completion}%</span>
                </div>
                <div className="mt-2 h-3 rounded-full bg-slate-200/80 dark:bg-white/10">
                  <div className="h-3 rounded-full bg-[#14B8A6]" style={{ width: `${site.completion}%` }} />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Worker Workload" eyebrow="Assignments" delay={0.15}>
          <div className="space-y-3">
            {data.workerLoad.map((worker) => (
              <div key={worker.name} className="rounded-2xl border border-white/10 bg-white/50 p-4 dark:bg-slate-950/40">
                <p className="font-medium text-slate-900 dark:text-white">{worker.name}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">{worker.openTasks} open tasks</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </DashboardLayout>
  );
}
