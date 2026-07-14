import { motion } from "framer-motion";
import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import type { RenewalCategory } from "../../lib/utils/policy-classifier";
import { daysUntilUTC } from "../../lib/utils/policy-classifier";
import {
  formatDaysRemaining,
  formatPolicyPremium,
  getPolicyMobile,
  type PolicyWithExtras,
} from "../../lib/utils/policy-display";
import { formatDate } from "../../lib/utils/formatDate";
import { SendReminderDialog } from "./send-reminder-dialog";
import { AlertTriangle, Bell } from "./icons";

const BADGE: Record<
  RenewalCategory,
  { label: string; bg: string; text: string; border: string }
> = {
  critical: {
    label: "Critical",
    bg: "rgba(239,68,68,0.15)",
    text: "#F87171",
    border: "rgba(239,68,68,0.35)",
  },
  due_soon: {
    label: "Due Renewals",
    bg: "rgba(249,115,22,0.15)",
    text: "#FB923C",
    border: "rgba(249,115,22,0.35)",
  },
  upcoming: {
    label: "Upcoming",
    bg: "rgba(59,130,246,0.15)",
    text: "#60A5FA",
    border: "rgba(59,130,246,0.35)",
  },
};

type RenewalPolicyCardProps = {
  policy: PolicyWithExtras;
  category: RenewalCategory;
  onMarkRenewed: (policyId: number) => void;
  isRenewing?: boolean;
  index?: number;
};

export function RenewalPolicyCard({
  policy,
  category,
  onMarkRenewed,
  isRenewing,
  index = 0,
}: RenewalPolicyCardProps) {
  const navigate = useNavigate();
  const [reminderOpen, setReminderOpen] = useState(false);
  const badge = BADGE[category];
  const mobile = getPolicyMobile(policy);
  const days = daysUntilUTC(policy.expiry_date);

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
      className={`gyantra-glass-card overflow-hidden ${
        category === "critical" ? "ring-1 ring-red-500/30" : ""
      }`}
    >
      {category === "critical" ? (
        <div className="flex items-center gap-2 border-b border-red-500/20 bg-red-500/10 px-4 py-2">
          <AlertTriangle className="h-4 w-4 text-red-400" />
          <span className="text-xs font-semibold uppercase tracking-wide text-red-400">
            High Priority — expires in {days === 0 ? "today" : `${days} day${days === 1 ? "" : "s"}`}
          </span>
        </div>
      ) : null}

      <div className="p-4 md:p-5">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-lg font-semibold text-white">{policy.policyholder_name}</p>
            <p className="text-sm text-slate-400">{policy.policy_number}</p>
          </div>
          <span
            className="rounded-full px-3 py-1 text-xs font-semibold"
            style={{
              background: badge.bg,
              color: badge.text,
              border: `1px solid ${badge.border}`,
            }}
          >
            {badge.label}
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm md:grid-cols-4">
          <div>
            <dt className="text-xs text-slate-500">Policy Type</dt>
            <dd className="mt-0.5 font-medium text-slate-200">{policy.policy_type || "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Mobile Number</dt>
            <dd className="mt-0.5 font-medium text-slate-200">{mobile}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Expiry Date</dt>
            <dd className="mt-0.5 font-medium text-slate-200">{formatDate(policy.expiry_date)}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Days Remaining</dt>
            <dd className="mt-0.5 font-semibold text-white">{formatDaysRemaining(policy)}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Premium Amount</dt>
            <dd className="mt-0.5 font-medium text-slate-200">{formatPolicyPremium(policy)}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Status</dt>
            <dd className="mt-0.5 capitalize text-slate-200">{policy.status || "active"}</dd>
          </div>
        </dl>

        <div className="mt-5 flex flex-wrap gap-2 border-t border-white/6 pt-4">
          <button
            type="button"
            onClick={() => navigate(`/app/insurance/policies/${policy.id}`)}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[#14B8A6]/40 hover:bg-[#14B8A6]/10 hover:text-white"
          >
            View Policy
          </button>
          <button
            type="button"
            onClick={() => setReminderOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[#14B8A6]/40 hover:bg-[#14B8A6]/10 hover:text-white"
          >
            <Bell className="h-3.5 w-3.5" />
            Send Reminder
          </button>
          <button
            type="button"
            disabled={isRenewing}
            onClick={() => onMarkRenewed(policy.id)}
            className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
          >
            {isRenewing ? "Processing…" : "Mark Renewal Completed"}
          </button>
        </div>
      </div>

      <SendReminderDialog policy={policy} open={reminderOpen} onClose={() => setReminderOpen(false)} />
    </motion.article>
  );
}

type RenewalSectionProps = {
  id: string;
  title: string;
  description: string;
  count: number;
  highlight?: boolean;
  highlightRingClass?: string;
  icon: ReactNode;
  accentColor: string;
  children: ReactNode;
};

export function RenewalSection({
  id,
  title,
  description,
  count,
  highlight,
  highlightRingClass = "ring-orange-400",
  icon,
  accentColor,
  children,
}: RenewalSectionProps) {
  return (
    <section
      id={id}
      className={`scroll-mt-24 rounded-[20px] transition-all duration-500 ${
        highlight ? `ring-2 ${highlightRingClass} ring-offset-2 ring-offset-[#050816]` : ""
      }`}
    >
      <div
        className={`mb-4 flex flex-wrap items-center justify-between gap-3 ${
          highlight ? "animate-pulse" : ""
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl"
            style={{ background: `${accentColor}22`, color: accentColor }}
          >
            {icon}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">{title}</h2>
            <p className="text-sm text-slate-400">{description}</p>
          </div>
        </div>
        <span
          className="rounded-full px-3 py-1 text-sm font-bold text-white"
          style={{ background: `${accentColor}33`, color: accentColor }}
        >
          {count}
        </span>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

export function RenewalSectionEmpty({ message }: { message: string }) {
  return (
    <div className="gyantra-glass-card px-4 py-6 text-center text-sm text-slate-500">{message}</div>
  );
}
