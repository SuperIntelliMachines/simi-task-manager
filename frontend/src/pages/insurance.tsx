import { useMemo } from "react";
import { useWorkbench } from "../app/providers/workbench-provider";
import { useInsuranceDashboard, useListFollowups, useListPolicies } from "../lib/api/hooks";
import { classifyPolicySummaryKpis } from "../lib/utils/policy-classifier";
import { classifyLeadFollowupOverview } from "../lib/utils/lead-followup-classifier";
import { buildRenewalIntelligenceChart, type RenewalIntelligenceChart } from "../lib/utils/renewal-intelligence";
import { InsuranceHero } from "../components/insurance/insurance-hero";
import { PolicySummarySection } from "../components/insurance/policy-summary-section";
import { LeadFollowupOverviewSection } from "../components/insurance/lead-followup-overview-section";
import { RenewalIntelligenceSection } from "../components/insurance/renewal-intelligence-section";
import { DashboardLayout, EmptyState, LoadingState } from "../components/design-system";

export function InsurancePage() {
  const { organizationId, currentUserName } = useWorkbench();

  const dashboardQuery = useInsuranceDashboard(organizationId);
  const followupsQuery = useListFollowups(organizationId);
  const policiesQuery = useListPolicies(organizationId);

  const allPolicies = policiesQuery.data ?? [];
  const dashboard = dashboardQuery.data;

  const allFollowups = followupsQuery.data ?? dashboard?.pending_followups ?? [];

  const policySummary = useMemo(() => {
    if (dashboard?.policy_summary) {
      return dashboard.policy_summary;
    }
    return classifyPolicySummaryKpis(allPolicies);
  }, [dashboard?.policy_summary, allPolicies]);

  const leadFollowupOverview = useMemo(() => {
    if (dashboard?.lead_followup_overview) {
      return dashboard.lead_followup_overview;
    }
    return classifyLeadFollowupOverview(allFollowups);
  }, [dashboard?.lead_followup_overview, allFollowups]);

  const renewalIntelligence = useMemo((): RenewalIntelligenceChart => {
    if (dashboard?.renewal_intelligence) {
      return dashboard.renewal_intelligence as RenewalIntelligenceChart;
    }
    return buildRenewalIntelligenceChart(allPolicies);
  }, [dashboard?.renewal_intelligence, allPolicies]);

  const isLoading =
    (dashboardQuery.isLoading || policiesQuery.isLoading) &&
    !dashboardQuery.data &&
    allPolicies.length === 0;

  const isEmpty = useMemo(() => {
    if (dashboardQuery.isSuccess && dashboard) {
      const policySummaryCount = dashboard.policy_summary?.total_policies ?? 0;
      const policyListCount =
        allPolicies.length ||
        dashboard.due_renewals?.length ||
        dashboard.expiring_policies?.length ||
        dashboard.grace_period_policies?.length ||
        dashboard.lapsed_policies?.length ||
        0;
      const totalPolicies = Math.max(policySummaryCount, policyListCount);

      const leadSummaryCount = dashboard.lead_followup_overview?.total_leads ?? 0;
      const leadListCount = allFollowups.length || dashboard.pending_followups?.length || 0;
      const totalLeads = Math.max(leadSummaryCount, leadListCount);
      return totalPolicies === 0 && totalLeads === 0;
    }
    return policySummary.total_policies === 0 && leadFollowupOverview.total_leads === 0;
  }, [
    dashboardQuery.isSuccess,
    dashboard,
    allPolicies.length,
    allFollowups.length,
    policySummary.total_policies,
    leadFollowupOverview.total_leads,
  ]);

  if (organizationId == null) {
    return <LoadingState label="Loading organization..." />;
  }

  return (
    <DashboardLayout>
      <InsuranceHero userName={currentUserName} />

      {isLoading ? <LoadingState label="Loading insurance dashboard..." /> : null}

      {!isLoading && isEmpty ? (
        <EmptyState message="No insurance activity yet. Start with a policy or lead workflow." />
      ) : null}

      {!isLoading && !isEmpty ? (
        <>
          <PolicySummarySection counts={policySummary} />
          <LeadFollowupOverviewSection counts={leadFollowupOverview} />
          <RenewalIntelligenceSection data={renewalIntelligence} />
        </>
      ) : null}
    </DashboardLayout>
  );
}
