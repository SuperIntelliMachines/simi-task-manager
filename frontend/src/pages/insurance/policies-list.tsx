import React, { useMemo, useState } from "react";
import { useWorkbench } from "../../app/providers/workbench-provider";
import { useListPolicies } from "../../lib/api/hooks";
import {
  isExpiring,
  isDue,
  isExpiringSoonPolicy,
  isGracePeriod,
  isLapsed,
  sortPoliciesByDefaultOrder,
  classifyPolicy,
} from "../../lib/utils/policy-classifier";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { Link, useSearchParams } from "react-router-dom";
import {
  parsePolicyListFilter,
  POLICY_LIST_FILTER_DESCRIPTIONS,
  POLICY_LIST_FILTER_LABELS,
  policyListPath,
} from "../../lib/insurance/policy-list-navigation";
import type { InsurancePolicyCard } from "../../lib/api/types";
import { PolicyListCard } from "../../components/insurance/policy-list-card";
import { PolicyListToolbar } from "../../components/insurance/policy-list-toolbar";

export function PoliciesListPage() {
  const { organizationId } = useWorkbench();
  const orgId = organizationId;
  const [searchParams, setSearchParams] = useSearchParams();
  const statusParam = searchParams.get("status");
  const filterParam = searchParams.get("filter");
  const activeFilter = parsePolicyListFilter(filterParam) ?? parsePolicyListFilter(statusParam);
  const daysParam = searchParams.get("days");
  const qParam = searchParams.get("q") || "";
  const carrierParam = searchParams.get("carrier") || "";
  const typeParam = searchParams.get("type") || "";
  const expiryParam = searchParams.get("expiry") || "";
  const rawSortParam = searchParams.get("sort");
  const sortParam = !rawSortParam || rawSortParam === "priority" ? "default" : rawSortParam;

  const [searchInput, setSearchInput] = useState<string>(qParam);

  const allPoliciesQuery = useListPolicies(orgId);
  const activeQuery = useListPolicies(orgId, "active");

  function daysUntil(dateIso: string) {
    try {
      const d = new Date(dateIso);
      const now = new Date();
      const utcStart = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
      const utcTarget = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
      const diff = (utcTarget - utcStart) / (1000 * 60 * 60 * 24);
      return Math.round(diff);
    } catch {
      return NaN;
    }
  }

  // Use unified classifier for filters so counts and lists match
  let query: any;
  const rawPolicies = allPoliciesQuery.data ?? [];
  if (activeFilter === "due") {
    query = {
      isLoading: allPoliciesQuery.isLoading,
      isError: allPoliciesQuery.isError,
      data: rawPolicies ? rawPolicies.filter((p: any) => isDue(p)) : [],
    };
  } else if (activeFilter === "expiring") {
    const days = daysParam ? Number(daysParam) : 2;
    query = {
      isLoading: allPoliciesQuery.isLoading,
      isError: allPoliciesQuery.isError,
      data: rawPolicies ? rawPolicies.filter((p: any) => isExpiring(p, days)) : [],
    };
  } else if (activeFilter === "expiring_soon") {
    query = {
      isLoading: allPoliciesQuery.isLoading,
      isError: allPoliciesQuery.isError,
      data: rawPolicies ? rawPolicies.filter((p: any) => isExpiringSoonPolicy(p)) : [],
    };
  } else if (activeFilter === "grace_period") {
    query = {
      isLoading: allPoliciesQuery.isLoading,
      isError: allPoliciesQuery.isError,
      data: rawPolicies ? rawPolicies.filter((p: any) => isGracePeriod(p)) : [],
    };
  } else if (activeFilter === "lapsed") {
    query = {
      isLoading: allPoliciesQuery.isLoading,
      isError: allPoliciesQuery.isError,
      data: rawPolicies ? rawPolicies.filter((p: any) => isLapsed(p)) : [],
    };
  } else if (activeFilter === "active") {
    query = activeQuery;
  } else {
    query = allPoliciesQuery;
  }

  console.log('PoliciesListPage: organizationId', organizationId);

  // Debug: log all policies with expiry and computed daysRemaining/category
    if (allPoliciesQuery.data) {
    const nowUtc = new Date().toUTCString();
    allPoliciesQuery.data.forEach((p) => {
      try {
        const d = p.expiry_date;
        const { category, daysRemaining } = classifyPolicy(p);
        console.log && console.log('[PoliciesList.debug]', { policy_number: p.policy_number, policyholder_name: p.policyholder_name, expiry: d, utc_today: nowUtc, daysRemaining, category });
      } catch (e) {
        console.log && console.log('[PoliciesList.debug] parse error', p.policy_number, e);
      }
    });
    // Summary totals for quick verification
    try {
      const total = allPoliciesQuery.data.length;
      const activeCount = activeQuery.data ? activeQuery.data.length : allPoliciesQuery.data.filter((p: any) => !(isLapsed(p) || isGracePeriod(p) || isExpiring(p, 2) || isDue(p))).length;
      const expiringCount = allPoliciesQuery.data.filter((p: any) => isExpiring(p, 2)).length;
      const dueCount = allPoliciesQuery.data.filter((p: any) => isDue(p)).length;
      const graceCount = allPoliciesQuery.data.filter((p: any) => isGracePeriod(p)).length;
      const lapsedCount = allPoliciesQuery.data.filter((p: any) => isLapsed(p)).length;
      console.log && console.log('[PoliciesList.summary]', { total, activeCount, expiringCount, dueCount, graceCount, lapsedCount });
    } catch (e) {
      /* ignore */
    }
  }
  // Client-side filters: search, carrier, type, expiry, sort
  const policiesFiltered = useMemo(() => {
    const list = (query.data || []).slice();
    const q = (searchInput || "").toLowerCase().trim();

    let out = list.filter((p: any) => {
      if (q) {
        const match = `${p.policyholder_name || ""} ${p.policy_number || ""}`.toLowerCase();
        if (!match.includes(q)) return false;
      }
      if (carrierParam && carrierParam !== "all") {
        if (!p.carrier || p.carrier.toLowerCase() !== carrierParam.toLowerCase()) return false;
      }
      if (typeParam && typeParam !== "all") {
        if (!p.policy_type || p.policy_type.toLowerCase() !== typeParam.toLowerCase()) return false;
      }
      if (expiryParam && expiryParam !== "all") {
        const days = daysUntil(p.expiry_date);
        if (expiryParam === "today" && days !== 0) return false;
        if (expiryParam === "7" && (isNaN(days) || days < 0 || days > 7)) return false;
        if (expiryParam === "30" && (isNaN(days) || days < 0 || days > 30)) return false;
        if (expiryParam === "past_due" && days >= 0) return false;
      }
      return true;
    });

    if (sortParam === "oldest") {
      out.sort((a: any, b: any) => new Date(a.created_at || a.created || 0).getTime() - new Date(b.created_at || b.created || 0).getTime());
    } else if (sortParam === "expiry") {
      out.sort((a: any, b: any) => new Date(a.expiry_date || 0).getTime() - new Date(b.expiry_date || 0).getTime());
    } else if (sortParam === "name") {
      out.sort((a: any, b: any) => String(a.policyholder_name || "").localeCompare(String(b.policyholder_name || "")));
    } else if (sortParam === "newest") {
      out.sort((a: any, b: any) => new Date(b.created_at || b.created || 0).getTime() - new Date(a.created_at || a.created || 0).getTime());
    } else {
      out = sortPoliciesByDefaultOrder(out);
    }

    return out;
  }, [query.data, searchInput, carrierParam, typeParam, expiryParam, sortParam]);

  if (organizationId == null) return <Loading label="Loading organization..." />;
  if (query.isLoading) return <Loading label="Loading policies..." />;
  if (query.isError) return <ErrorState message="Failed to load policies" />;

  const pageTitle = activeFilter ? POLICY_LIST_FILTER_LABELS[activeFilter] : POLICY_LIST_FILTER_LABELS.all;
  const pageDescription = activeFilter ? POLICY_LIST_FILTER_DESCRIPTIONS[activeFilter] : undefined;
  const emptyMessage = activeFilter
    ? `No ${POLICY_LIST_FILTER_LABELS[activeFilter].toLowerCase()} found.`
    : "No policies found.";

  function handleToolbarFilterChange(key: string, value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (key === "filter") {
      params.delete("status");
      if (!value) params.delete("filter");
      else params.set("filter", value);
    } else if (!value) {
      params.delete(key);
    } else {
      params.set(key, value);
    }
    setSearchParams(params);
  }

  function handleSearchChange(value: string) {
    setSearchInput(value);
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("q", value);
    else params.delete("q");
    setSearchParams(params);
  }

  const pageHeader = (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white md:text-3xl">{pageTitle}</h1>
        {pageDescription ? (
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-gray-700 dark:text-slate-400 md:text-base">{pageDescription}</p>
        ) : null}
      </div>
      <Link to="/app/insurance/policies/create" className="btn shrink-0 self-start">
        Add Policy Holder
      </Link>
    </header>
  );

  const activeFilterChip = activeFilter ? (
    <div className="flex items-center gap-3">
      <span className="inline-flex items-center rounded-full border border-[#14B8A6]/30 bg-[#14B8A6]/10 px-3 py-1 text-xs font-semibold text-[#14B8A6]">
        {POLICY_LIST_FILTER_LABELS[activeFilter]}
      </span>
      <Link to={policyListPath()} className="text-sm font-medium text-[#14B8A6] hover:text-[#2dd4bf]">
        Clear filter
      </Link>
    </div>
  ) : null;

  const toolbar = (
    <PolicyListToolbar
      searchInput={searchInput}
      onSearchChange={handleSearchChange}
      activeFilter={activeFilter}
      carrierParam={carrierParam}
      typeParam={typeParam}
      expiryParam={expiryParam}
      sortParam={sortParam}
      onFilterChange={handleToolbarFilterChange}
    />
  );

  if (!query.data || query.data.length === 0) {
    return (
      <div className="relative space-y-5 pb-6">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-64 overflow-hidden" aria-hidden>
          <div className="absolute -right-16 top-0 h-56 w-56 rounded-full bg-[#8B5CF6]/10 blur-3xl" />
          <div className="absolute left-1/4 top-8 h-40 w-40 rounded-full bg-[#14B8A6]/10 blur-3xl" />
        </div>
        <div className="relative space-y-5">
          {pageHeader}
          {activeFilterChip}
          {toolbar}
          <EmptyState message={emptyMessage} />
        </div>
      </div>
    );
  }

  // Log policies from API for verification
  console.log('Policies from API:', query.data);
  console.log('Policy count:', query.data.length);

  return (
    <div className="relative space-y-5 pb-6">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-64 overflow-hidden" aria-hidden>
        <div className="absolute -right-16 top-0 h-56 w-56 rounded-full bg-[#8B5CF6]/10 blur-3xl" />
        <div className="absolute left-1/4 top-8 h-40 w-40 rounded-full bg-[#14B8A6]/10 blur-3xl" />
      </div>

      <div className="relative space-y-5">
        {pageHeader}
        {activeFilterChip}
        {toolbar}

        <p className="text-sm font-medium text-gray-600 dark:text-slate-500">
          Showing <span className="text-gray-900 dark:text-slate-300">{policiesFiltered.length}</span>{" "}
          {policiesFiltered.length === 1 ? "Policy" : "Policies"}
        </p>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {policiesFiltered.map((p: InsurancePolicyCard, index: number) => (
            <PolicyListCard key={p.id} policy={p} index={index} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default PoliciesListPage;
