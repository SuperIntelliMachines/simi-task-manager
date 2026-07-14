import { useWorkbench } from "../app/providers/workbench-provider";
import { useMedicalDashboard } from "../lib/api/hooks";
import {
  DashboardLayout,
  HeroBadge,
  HeroBanner,
  LoadingState,
  SectionCard,
} from "../components/design-system";
import { Sparkles } from "../components/insurance/icons";

function redact(value: string, shouldRedact: boolean) {
  return shouldRedact ? "[REDACTED]" : value;
}

export function MedicalOfficePage() {
  const { role, currentUserName } = useWorkbench();
  const dashboardQuery = useMedicalDashboard();
  const shouldRedact = role === "viewer";

  if (!dashboardQuery.data) {
    return (
      <DashboardLayout>
        <LoadingState label="Loading medical office dashboard..." />
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
            label="Medical Office"
          />
        }
        subtitle="Tomorrow prep and internal queues. Viewer role automatically redacts sensitive patient details."
      />

      <div className="grid gap-6 xl:grid-cols-3">
        <SectionCard title="Tomorrow Prep" eyebrow="Redaction Aware" delay={0.05}>
          <div className="space-y-3">
            {data.tomorrowPrep.map((item) => (
              <div key={item.id} className="rounded-2xl border border-white/10 bg-white/50 p-4 dark:bg-slate-950/40">
                <p className="font-medium text-slate-900 dark:text-white">{redact(item.patient, shouldRedact)}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {shouldRedact ? "Visit summary hidden for viewer role." : item.summary}
                </p>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Overdue Internal Tasks" eyebrow="Operations" delay={0.1}>
          <div className="rounded-2xl border border-white/10 bg-white/50 p-4 dark:bg-slate-950/40">
            <p className="text-sm text-slate-600 dark:text-slate-400">Tasks needing action</p>
            <p className="mt-1 text-4xl font-semibold text-slate-900 dark:text-white">{data.overdueInternalTasks}</p>
          </div>
        </SectionCard>

        <SectionCard title="Referral and Billing Queues" eyebrow="Restricted Details" delay={0.15}>
          <div className="space-y-3">
            {data.queues.map((queue) => (
              <div key={queue.id} className="rounded-2xl border border-white/10 bg-white/50 p-4 dark:bg-slate-950/40">
                <p className="font-medium text-slate-900 dark:text-white">{redact(queue.patient, shouldRedact)}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">Lane: {queue.lane}</p>
                <p className="text-sm text-slate-500 dark:text-slate-500">Owner: {queue.owner}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </DashboardLayout>
  );
}
