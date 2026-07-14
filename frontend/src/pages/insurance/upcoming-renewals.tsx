import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListPolicies, useRenewPolicy } from "../../lib/api/hooks";
import { categorizeRenewals, classifyDashboardKpis, isDue, isExpiring } from "../../lib/utils/policy-classifier";
import type { PolicyWithExtras } from "../../lib/utils/policy-display";
import {
  RenewalPolicyCard,
  RenewalSection,
  RenewalSectionEmpty,
} from "../../components/insurance/renewal-policy-card";
import { AlertTriangle, Clock } from "../../components/insurance/icons";
import { GlassCard } from "../../components/insurance/glass-card";

export function UpcomingRenewalsPage() {
  const { organizationId } = useWorkbench();
  const [searchParams] = useSearchParams();
  const highlightSection = searchParams.get("section");
  const [renewingId, setRenewingId] = useState<number | null>(null);

  const policiesQuery = useListPolicies(organizationId);
  const renewMutation = useRenewPolicy(organizationId);

  const allPolicies = (policiesQuery.data ?? []) as PolicyWithExtras[];

  const { critical, dueSoon, all } = useMemo(
    () => categorizeRenewals(allPolicies),
    [allPolicies]
  );

  const kpis = useMemo(() => classifyDashboardKpis(allPolicies), [allPolicies]);

  useEffect(() => {
    if (!highlightSection) return;
    const timer = window.setTimeout(() => {
      const el = document.getElementById(highlightSection);
      el?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [highlightSection, policiesQuery.isSuccess]);

  async function handleMarkRenewed(policyId: number) {
    setRenewingId(policyId);
    try {
      await renewMutation.mutateAsync({ policyId });
    } finally {
      setRenewingId(null);
    }
  }

  if (organizationId == null) {
    return <p className="text-sm text-slate-400">Loading organization...</p>;
  }

  if (policiesQuery.isLoading) {
    return <p className="text-sm text-slate-400">Loading upcoming renewals...</p>;
  }

  const isEmpty = all.length === 0;

  return (
    <div className="space-y-6 pb-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
      >
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#14B8A6]">Insurance</p>
        <h1 className="mt-1 text-2xl font-bold text-white md:text-3xl">Upcoming Renewals</h1>
        <p className="mt-2 text-sm text-slate-400">
          Active policies expiring within the next 10 days, sorted by nearest expiry first.
        </p>
      </motion.div>

      {!isEmpty ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <GlassCard className="p-4">
            <p className="text-xs text-slate-500">Expiring (0–2 days)</p>
            <p className="text-2xl font-bold text-red-400">{critical.length}</p>
            <p className="text-xs text-slate-500">Matches Expiring KPI: {kpis.expiring}</p>
          </GlassCard>
          <GlassCard className="p-4">
            <p className="text-xs text-slate-500">Due Renewals (3–10 days)</p>
            <p className="text-2xl font-bold text-orange-400">{dueSoon.length}</p>
            <p className="text-xs text-slate-500">Matches Due Renewals KPI: {kpis.due}</p>
          </GlassCard>
        </div>
      ) : null}

      {isEmpty ? (
        <GlassCard className="p-10 text-center">
          <p className="text-lg font-semibold text-white">
            🎉 Great! No policy renewals are due in the next 10 days.
          </p>
          <p className="mt-2 text-sm text-slate-400">All active policies are currently up to date.</p>
        </GlassCard>
      ) : (
        <div className="space-y-10">
          <RenewalSection
            id="critical"
            title="Expiring Policies"
            description="Policies expiring in 0–2 days — immediate action required"
            count={critical.length}
            highlight={highlightSection === "critical"}
            highlightRingClass="ring-red-400"
            accentColor="#EF4444"
            icon={<AlertTriangle className="h-5 w-5" />}
          >
            {critical.length === 0 ? (
              <RenewalSectionEmpty message="No expiring policies at this time." />
            ) : (
              critical.map((policy, i) => (
                <RenewalPolicyCard
                  key={policy.id}
                  policy={policy}
                  category="critical"
                  index={i}
                  isRenewing={renewingId === policy.id}
                  onMarkRenewed={handleMarkRenewed}
                />
              ))
            )}
          </RenewalSection>

          <RenewalSection
            id="due-soon"
            title="Due Renewals"
            description="Policies expiring in 3–10 days"
            count={dueSoon.length}
            highlight={highlightSection === "due-soon" || highlightSection === "upcoming"}
            highlightRingClass="ring-orange-400"
            accentColor="#F97316"
            icon={<Clock className="h-5 w-5" />}
          >
            {dueSoon.length === 0 ? (
              <RenewalSectionEmpty message="No policies in the 3–10 day due renewal window." />
            ) : (
              dueSoon.map((policy, i) => (
                <RenewalPolicyCard
                  key={policy.id}
                  policy={policy}
                  category="due_soon"
                  index={i}
                  isRenewing={renewingId === policy.id}
                  onMarkRenewed={handleMarkRenewed}
                />
              ))
            )}
          </RenewalSection>
        </div>
      )}
    </div>
  );
}

export default UpcomingRenewalsPage;
