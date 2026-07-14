import React from "react";
import { Link } from "react-router-dom";
import type { InsurancePolicyCard } from "../../lib/api/types";
import { formatDate } from "../../lib/utils/formatDate";
import { getPolicyListStatusBadge } from "../../lib/utils/policy-display";

type PolicyCardProps = {
  item: InsurancePolicyCard;
  to?: string;
};

export function PolicyCard({ item, to }: PolicyCardProps) {
  const badge = getPolicyListStatusBadge(item);
  const href = to ?? `/app/insurance/policies/${item.id}`;

  return (
    <Link
      to={href}
      className="gyantra-glass-card group block h-full rounded-[20px] border border-white/40 dark:border-white/[0.08] p-5 shadow-[0_8px_30px_rgba(0,0,0,0.08)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.35)] transition-all duration-300 hover:-translate-y-1.5 hover:border-[#14B8A6]/25 hover:shadow-[0_16px_48px_rgba(0,0,0,0.16),0_0_24px_rgba(20,184,166,0.08)] dark:hover:shadow-[0_16px_48px_rgba(0,0,0,0.45),0_0_24px_rgba(20,184,166,0.08)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-lg font-semibold tracking-tight text-gray-900 dark:text-white group-hover:text-[#14B8A6] transition-colors">
            {item.policyholder_name}
          </p>
          <p className="mt-1 text-sm font-medium text-gray-700 dark:text-slate-400">{item.policy_number}</p>
        </div>
        <span
          className={`inline-flex shrink-0 items-center rounded-full px-3 py-1 text-xs font-semibold ${badge.className}`}
        >
          {badge.label}
        </span>
      </div>

      <div className="mt-5 space-y-2 border-t border-gray-200/80 dark:border-white/[0.06] pt-4 text-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="text-gray-600 dark:text-slate-500">Provider</span>
          <span className="truncate font-medium text-gray-800 dark:text-slate-200">{item.carrier ?? "—"}</span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-gray-600 dark:text-slate-500">Agent</span>
          <span className="truncate font-medium text-gray-800 dark:text-slate-200">
            {item.assigned_agent_user_id ?? "—"}
          </span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-gray-600 dark:text-slate-500">Renewal Date</span>
          <span className="font-medium text-gray-800 dark:text-slate-200">{formatDate(item.expiry_date)}</span>
        </div>
      </div>
    </Link>
  );
}

export default PolicyCard;
