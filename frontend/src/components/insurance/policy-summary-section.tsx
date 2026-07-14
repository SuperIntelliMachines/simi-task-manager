import { useNavigate } from "react-router-dom";
import { InsuranceStatCard } from "./insurance-stat-card";
import { policyListPath } from "../../lib/insurance/policy-list-navigation";
import { FileStack, ShieldCheck, XCircle } from "./icons";

export type PolicySummaryCounts = {
  total_policies: number;
  active_policies: number;
  grace_period_policies: number;
  lapsed_policies: number;
  expiring_soon_policies: number;
};

type PolicySummarySectionProps = {
  counts: PolicySummaryCounts;
};

export function PolicySummarySection({ counts }: PolicySummarySectionProps) {
  const navigate = useNavigate();

  return (
    <section className="space-y-4">
      <h3 className="text-lg font-bold text-black dark:text-foreground">Policy Summary</h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <InsuranceStatCard
          title="Total Policies"
          count={counts.total_policies}
          accent="teal"
          icon={<FileStack className="h-5 w-5" />}
          delay={0.05}
          onClick={() => navigate(policyListPath())}
        />
        <InsuranceStatCard
          title="Active Policies"
          count={counts.active_policies}
          accent="blue"
          icon={<ShieldCheck className="h-5 w-5" />}
          delay={0.1}
          onClick={() => navigate(policyListPath("active"))}
        />
        <InsuranceStatCard
          title="Grace Period"
          count={counts.grace_period_policies}
          accent="red"
          icon={<XCircle className="h-5 w-5" />}
          delay={0.15}
          onClick={() => navigate(policyListPath("grace_period"))}
        />
        <InsuranceStatCard
          title="Lapsed"
          count={counts.lapsed_policies}
          accent="pink"
          icon={<XCircle className="h-5 w-5" />}
          delay={0.2}
          onClick={() => navigate(policyListPath("lapsed"))}
        />
      </div>
    </section>
  );
}
