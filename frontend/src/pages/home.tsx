import { Link } from "react-router-dom";

import { useWorkbench } from "../app/providers/workbench-provider";
import {
  DashboardLayout,
  HeroBadge,
  HeroBanner,
  KpiCard,
  KpiGrid,
  QuickActions,
  SectionCard,
} from "../components/design-system";
import { Sparkles } from "../components/insurance/icons";

export function HomePage() {
  const { currentUserName } = useWorkbench();

  return (
    <DashboardLayout>
      <HeroBanner
        userName={currentUserName}
        badge={
          <HeroBadge
            icon={<Sparkles className="h-3.5 w-3.5 text-[#8B5CF6]" />}
            label="SIMI Operations Hub"
          />
        }
        subtitle="Manage tasks, reminders, AI workflows, and channel connections from one workspace."
      />

      <QuickActions
        actions={[
          { label: "Open Task Workbench", to: "/app/tasks" },
          { label: "AI Assistant", to: "/app/agents", variant: "outline" },
          { label: "Channel Settings", to: "/app/channels", variant: "outline" },
        ]}
      />

      <KpiGrid title="Workspace Overview" columns="4">
        <KpiCard title="Task Workbench" count={1} accent="teal" delay={0.05} icon={<span className="text-lg">✓</span>} />
        <KpiCard title="AI Assistant" count={1} accent="purple" delay={0.1} icon={<span className="text-lg">✦</span>} />
        <KpiCard title="Channels" count={4} accent="cyan" delay={0.15} icon={<span className="text-lg">◎</span>} />
        <KpiCard title="Reminders" count={1} accent="amber" delay={0.2} icon={<span className="text-lg">⏰</span>} />
      </KpiGrid>

      <div className="grid gap-6 lg:grid-cols-3">
        <SectionCard title="Tasks" eyebrow="Execution" delay={0.05}>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Create, filter, complete, snooze, and inspect tasks from one workspace.
          </p>
          <Link to="/app/tasks" className="mt-4 inline-flex text-sm font-medium text-[#14B8A6] hover:underline">
            Open tasks →
          </Link>
        </SectionCard>
        <SectionCard title="AI Assistant" eyebrow="Agents" delay={0.1}>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Preview natural-language actions, confidence, missing fields, and approval states.
          </p>
          <Link to="/app/agents" className="mt-4 inline-flex text-sm font-medium text-[#14B8A6] hover:underline">
            Open assistant →
          </Link>
        </SectionCard>
        <SectionCard title="Channels" eyebrow="Messaging" delay={0.15}>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Configure WhatsApp, Telegram, email, and SMS connections for your organization.
          </p>
          <Link to="/app/channels" className="mt-4 inline-flex text-sm font-medium text-[#14B8A6] hover:underline">
            Manage channels →
          </Link>
        </SectionCard>
      </div>
    </DashboardLayout>
  );
}
