import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { InsuranceLeadCard, InsurancePolicyCard } from "../../lib/api/types";
import { formatDate } from "../../lib/utils/formatDate";
import { getFollowupCustomerName } from "../../lib/utils/followup-display";
import { GlassCard } from "./glass-card";
import { AlertTriangle, Clock, Phone, XCircle } from "./icons";

type ActivityItem = {
  id: string;
  title: string;
  description: string;
  time: string;
  accent: "teal" | "blue" | "orange" | "red" | "purple";
  href?: string;
};

const ACCENT_BG: Record<ActivityItem["accent"], string> = {
  teal: "rgba(20,184,166,0.18)",
  blue: "rgba(59,130,246,0.18)",
  orange: "rgba(249,115,22,0.18)",
  red: "rgba(239,68,68,0.18)",
  purple: "rgba(139,92,246,0.18)",
};

const ACCENT_COLOR: Record<ActivityItem["accent"], string> = {
  teal: "#14B8A6",
  blue: "#3B82F6",
  orange: "#F97316",
  red: "#EF4444",
  purple: "#8B5CF6",
};

function relativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "Recently";
  const diff = new Date(dateStr).getTime() - Date.now();
  const days = Math.round(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  if (days === -1) return "Yesterday";
  if (days > 0) return `In ${days} days`;
  return `${Math.abs(days)} days ago`;
}

function iconForAccent(accent: ActivityItem["accent"]) {
  if (accent === "orange") return <AlertTriangle className="h-4 w-4" />;
  if (accent === "red") return <XCircle className="h-4 w-4" />;
  if (accent === "purple") return <Phone className="h-4 w-4" />;
  return <Clock className="h-4 w-4" />;
}

type RecentActivityProps = {
  dueRenewals: InsurancePolicyCard[];
  expiringPolicies: InsurancePolicyCard[];
  expiredPolicies: InsurancePolicyCard[];
  pendingFollowups: InsuranceLeadCard[];
};

export function RecentActivity({ dueRenewals, expiringPolicies, expiredPolicies, pendingFollowups }: RecentActivityProps) {
  const navigate = useNavigate();

  const items = useMemo(() => {
    const list: ActivityItem[] = [];

    expiringPolicies.slice(0, 2).forEach((p) => {
      list.push({
        id: `exp-${p.id}`,
        title: `${p.policyholder_name} policy expiring`,
        description: `${p.policy_number} · ${p.policy_type ?? "Policy"}`,
        time: relativeTime(p.expiry_date),
        accent: "orange",
        href: `/app/insurance/policies/${p.id}`,
      });
    });

    dueRenewals.slice(0, 2).forEach((p) => {
      list.push({
        id: `due-${p.id}`,
        title: `Renewal due for ${p.policyholder_name}`,
        description: `Expires ${formatDate(p.expiry_date)}`,
        time: relativeTime(p.expiry_date),
        accent: "blue",
        href: `/app/insurance/policies/${p.id}`,
      });
    });

    pendingFollowups.slice(0, 2).forEach((f) => {
      list.push({
        id: `fu-${f.id}`,
        title: `Follow-up: ${getFollowupCustomerName(f)}`,
        description: "Customer decision pending",
        time: relativeTime(f.followup_due_at),
        accent: "purple",
        href: `/app/insurance/followups/${f.id}`,
      });
    });

    expiredPolicies.slice(0, 1).forEach((p) => {
      list.push({
        id: `expired-${p.id}`,
        title: `${p.policyholder_name} policy expired`,
        description: p.policy_number,
        time: relativeTime(p.expiry_date),
        accent: "red",
        href: `/app/insurance/policies/${p.id}`,
      });
    });

    return list.slice(0, 5);
  }, [dueRenewals, expiringPolicies, expiredPolicies, pendingFollowups]);

  return (
    <GlassCard delay={0.3} className="flex h-full flex-col p-5 md:p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
        <button
          type="button"
          onClick={() => navigate("/app/insurance/followups")}
          className="text-xs font-medium text-[#14B8A6] transition hover:text-[#5EEAD4]"
        >
          View all
        </button>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-slate-500">No recent insurance activity.</p>
      ) : (
        <ul className="space-y-4">
          {items.map((item, i) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => item.href && navigate(item.href)}
                className="flex w-full items-start gap-3 rounded-xl p-2 text-left transition hover:bg-white/5"
              >
                <div
                  className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg"
                  style={{ background: ACCENT_BG[item.accent], color: ACCENT_COLOR[item.accent] }}
                >
                  {iconForAccent(item.accent)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-white">{item.title}</p>
                  <p className="truncate text-xs text-slate-400">{item.description}</p>
                  <p className="mt-0.5 text-[11px] text-slate-500">{item.time}</p>
                </div>
              </button>
              {i < items.length - 1 ? <div className="ml-12 mt-4 h-px bg-white/6" /> : null}
            </li>
          ))}
        </ul>
      )}
    </GlassCard>
  );
}
