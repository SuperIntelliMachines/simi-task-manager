import { useNavigate } from "react-router-dom";
import type { InsurancePolicyCard } from "../../lib/api/types";
import { formatDate } from "../../lib/utils/formatDate";
import { daysUntilUTC, getRenewalCategory } from "../../lib/utils/policy-classifier";
import { GlassCard } from "./glass-card";
import { Clock } from "./icons";

type UpcomingRenewalsProps = {
  policies: InsurancePolicyCard[];
};

function urgencyStyle(category: ReturnType<typeof getRenewalCategory>) {
  if (category === "critical") return { bg: "rgba(239,68,68,0.15)", text: "#F87171", label: "Critical" };
  if (category === "due_soon") return { bg: "rgba(249,115,22,0.15)", text: "#FB923C", label: "Due Soon" };
  return { bg: "rgba(59,130,246,0.15)", text: "#60A5FA", label: "Upcoming" };
}

export function UpcomingRenewals({ policies }: UpcomingRenewalsProps) {
  const navigate = useNavigate();
  const sorted = [...policies]
    .sort((a, b) => new Date(a.expiry_date).getTime() - new Date(b.expiry_date).getTime())
    .slice(0, 6);

  return (
    <GlassCard delay={0.35} className="p-5 md:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Upcoming Renewals</h3>
          <p className="text-sm text-slate-400">Policies expiring within the next 30 days</p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/app/insurance/renewals/upcoming")}
          className="text-xs font-medium text-[#14B8A6] transition hover:text-[#5EEAD4]"
        >
          View all renewals
        </button>
      </div>

      {sorted.length === 0 ? (
        <p className="text-sm text-slate-500">No upcoming renewals in the pipeline.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sorted.map((policy) => {
            const days = daysUntilUTC(policy.expiry_date);
            const category = getRenewalCategory(policy);
            const style = urgencyStyle(category);
            return (
              <button
                key={policy.id}
                type="button"
                onClick={() => navigate(`/app/insurance/policies/${policy.id}`)}
                className="group flex items-center gap-3 rounded-xl border border-white/6 bg-white/3 p-4 text-left transition hover:border-[#14B8A6]/30 hover:bg-white/5"
              >
                <div
                  className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
                  style={{ background: style.bg, color: style.text }}
                >
                  <Clock className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-white">{policy.policyholder_name}</p>
                  <p className="truncate text-xs text-slate-400">{policy.policy_number}</p>
                  <p className="mt-1 text-xs text-slate-500">Expires {formatDate(policy.expiry_date)}</p>
                </div>
                <span
                  className="flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                  style={{ background: style.bg, color: style.text }}
                >
                  {days <= 0 ? "Today" : `${days}d`}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </GlassCard>
  );
}
