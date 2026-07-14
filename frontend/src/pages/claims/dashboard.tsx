import { DashboardLayout, HeroBadge, HeroBanner, SectionCard } from "../../components/design-system";
import { Sparkles } from "../../components/insurance/icons";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { CLAIMS_WORKSPACE_NAME } from "../../lib/claims/navigation";

export function ClaimsDashboardPage() {
  const { currentUser } = useWorkbench();
  const userName = currentUser?.email?.split("@")[0] ?? "Claims user";

  return (
    <DashboardLayout>
      <HeroBanner
        userName={userName}
        badge={<HeroBadge icon={<Sparkles className="h-3.5 w-3.5 text-[#14B8A6]" />} label={CLAIMS_WORKSPACE_NAME} />}
        subtitle="Monitor service cases, reminder activity, and claims operations in one place."
      />
      <SectionCard title="Claims Overview" eyebrow={CLAIMS_WORKSPACE_NAME}>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          This is the dedicated Claims dashboard. Service case metrics and operational widgets will appear here.
        </p>
      </SectionCard>
    </DashboardLayout>
  );
}
