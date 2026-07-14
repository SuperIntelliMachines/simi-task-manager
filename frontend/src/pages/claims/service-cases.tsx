import { DashboardLayout, SectionCard } from "../../components/design-system";
import { CLAIMS_WORKSPACE_NAME } from "../../lib/claims/navigation";

export function ClaimsServiceCasesPage() {
  return (
    <DashboardLayout>
      <SectionCard title="Service Cases" eyebrow={CLAIMS_WORKSPACE_NAME}>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Service case management for the Claims organization will be available here.
        </p>
      </SectionCard>
    </DashboardLayout>
  );
}
