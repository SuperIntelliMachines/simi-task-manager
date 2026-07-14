import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  filterRenewalIntelligenceTablePoints,
  formatDaysToRenewal,
  formatExpiryLabel,
  formatPremiumInr,
  renewalIntelligencePolicyStatus,
  RENEWAL_INTELLIGENCE_TABLE_POLICY_STATUSES,
  RENEWAL_INTELLIGENCE_TABLE_POLICY_TYPES,
  sortRenewalIntelligencePointsByExpiry,
  type RenewalIntelligencePoint,
  type RenewalIntelligencePolicyStatus,
} from "../../lib/utils/renewal-intelligence";
import { formatRenewalFrequencyLabel } from "../../lib/insurance/renewal-frequency";

const PAGE_SIZE = 10;

const filterSelectClassName =
  "w-full rounded-xl border border-white/10 bg-slate-950/40 px-3 h-11 text-sm text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40";

type RenewalIntelligenceDetailsTableProps = {
  points: RenewalIntelligencePoint[];
};

function ChevronLeftIcon({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightIcon({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PaginationArrow({
  direction,
  disabled,
  onClick,
}: {
  direction: "previous" | "next";
  disabled: boolean;
  onClick: () => void;
}) {
  const label = direction === "previous" ? "Previous page" : "Next page";

  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-white/10 text-slate-300 transition hover:border-[#14B8A6]/40 hover:text-white disabled:cursor-not-allowed disabled:border-white/5 disabled:text-slate-600 disabled:hover:border-white/5 disabled:hover:text-slate-600"
    >
      {direction === "previous" ? <ChevronLeftIcon /> : <ChevronRightIcon />}
    </button>
  );
}

function StatusBadge({ status }: { status: RenewalIntelligencePolicyStatus }) {
  const className =
    status === "Lapsed"
      ? "bg-red-500/15 text-red-300 ring-red-500/30"
      : status === "Grace Period"
        ? "bg-amber-500/15 text-amber-300 ring-amber-500/30"
        : "bg-cyan-500/15 text-cyan-300 ring-cyan-500/30";

  return (
    <span
      className={`inline-flex h-9 min-w-[120px] items-center justify-center whitespace-nowrap rounded-full px-4 text-center text-sm font-semibold leading-none ring-1 ring-inset ${className}`}
    >
      {status}
    </span>
  );
}

export function RenewalIntelligenceDetailsTable({ points }: RenewalIntelligenceDetailsTableProps) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [policyTypeFilter, setPolicyTypeFilter] = useState("");
  const [policyStatusFilter, setPolicyStatusFilter] = useState("");

  const filteredPoints = useMemo(
    () => filterRenewalIntelligenceTablePoints(points, policyTypeFilter, policyStatusFilter),
    [points, policyTypeFilter, policyStatusFilter]
  );

  const sortedPoints = useMemo(() => sortRenewalIntelligencePointsByExpiry(filteredPoints), [filteredPoints]);
  const totalPages = Math.max(1, Math.ceil(sortedPoints.length / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
  }, [points, policyTypeFilter, policyStatusFilter]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const pageStart = (page - 1) * PAGE_SIZE;
  const pageEnd = Math.min(pageStart + PAGE_SIZE, sortedPoints.length);
  const pageRows = sortedPoints.slice(pageStart, pageStart + PAGE_SIZE);

  if (sortedPoints.length === 0) {
    return (
      <div className="mt-6 rounded-xl border border-white/10 bg-slate-950/25 px-6 py-10 text-center">
        <h4 className="text-sm font-semibold text-white">Renewal Intelligence Details</h4>
        <p className="mt-2 text-sm text-slate-400">No policies found</p>
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-4">
      <h4 className="text-sm font-semibold text-white">Renewal Intelligence Details</h4>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-sm text-slate-400">Policy Type Filter</span>
          <select
            value={policyTypeFilter}
            onChange={(event) => setPolicyTypeFilter(event.target.value)}
            className={filterSelectClassName}
          >
            <option value="">All</option>
            {RENEWAL_INTELLIGENCE_TABLE_POLICY_TYPES.map((policyType) => (
              <option key={policyType} value={policyType}>
                {policyType}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-2 block text-sm text-slate-400">Policy Status Filter</span>
          <select
            value={policyStatusFilter}
            onChange={(event) => setPolicyStatusFilter(event.target.value)}
            className={filterSelectClassName}
          >
            <option value="">All</option>
            {RENEWAL_INTELLIGENCE_TABLE_POLICY_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-950/25">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3 font-medium">Customer Name</th>
              <th className="px-4 py-3 font-medium">Policy Number</th>
              <th className="px-4 py-3 font-medium">Policy Type</th>
              <th className="px-4 py-3 font-medium">Renewal Frequency</th>
              <th className="px-4 py-3 font-medium">Premium Amount</th>
              <th className="px-4 py-3 font-medium">Renewal Date</th>
              <th className="px-4 py-3 font-medium">Days to Renewal</th>
              <th className="px-4 py-3 font-medium">Policy Status</th>
              <th className="px-4 py-3 font-medium text-right">Reminders Sent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {pageRows.map((point) => {
              const policyStatus = renewalIntelligencePolicyStatus(point);
              return (
                <tr
                  key={point.policy_id}
                  className="cursor-pointer text-slate-200 transition hover:bg-white/5"
                  onClick={() => navigate(`/app/insurance/policies/${point.policy_id}`)}
                >
                  <td className="px-4 py-3 font-medium text-white">{point.customer_name}</td>
                  <td className="px-4 py-3 text-slate-300">{point.policy_number}</td>
                  <td className="px-4 py-3 text-slate-300">{point.product_type ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{formatRenewalFrequencyLabel(point.renewal_frequency)}</td>
                  <td className="px-4 py-3 text-slate-300">{formatPremiumInr(point.premium)}</td>
                  <td className="px-4 py-3 text-slate-300">{formatExpiryLabel(point.expiry_date)}</td>
                  <td className="px-4 py-3 text-slate-300">{formatDaysToRenewal(point)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={policyStatus} />
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                    {point.reminders_sent_count ?? 0}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-xs">
        <span className="tabular-nums text-slate-400">
          {pageStart + 1}-{pageEnd} of {sortedPoints.length} policies
        </span>
        <div className="ml-auto flex items-center gap-2">
          <PaginationArrow
            direction="previous"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          />
          <span className="min-w-[4.5rem] text-center tabular-nums text-slate-300">
            Page {page}/{totalPages}
          </span>
          <PaginationArrow
            direction="next"
            disabled={page >= totalPages}
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
          />
        </div>
      </div>
    </div>
  );
}
