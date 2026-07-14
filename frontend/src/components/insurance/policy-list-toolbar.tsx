import Combobox from "../ui/Combobox";

const FILTER_CONTROL_CLASS =
  "h-12 w-full shrink-0 rounded-xl border border-gray-300 bg-white/80 dark:border-white/10 dark:bg-slate-950/40 px-3 text-sm font-medium text-gray-800 dark:text-white hover:border-[#14B8A6]/40 transition-colors sm:w-36";

type PolicyListToolbarProps = {
  searchInput: string;
  onSearchChange: (value: string) => void;
  activeFilter: string | null;
  carrierParam: string;
  typeParam: string;
  expiryParam: string;
  sortParam: string;
  onFilterChange: (key: string, value: string | null) => void;
};

export function PolicyListToolbar({
  searchInput,
  onSearchChange,
  activeFilter,
  carrierParam,
  typeParam,
  expiryParam,
  sortParam,
  onFilterChange,
}: PolicyListToolbarProps) {
  return (
    <div className="gyantra-glass-card border border-white/[0.08] px-4 py-4 shadow-[0_8px_32px_rgba(0,0,0,0.35),0_0_24px_rgba(20,184,166,0.04)] md:px-5 md:py-3">
      <div className="flex flex-wrap items-center gap-3 md:flex-nowrap md:gap-4">
        <div className="relative w-full md:w-[38%] md:min-w-[240px] md:max-w-[420px] md:flex-shrink-0 lg:w-[40%]">
          <svg
            className="pointer-events-none absolute left-4 top-1/2 z-10 h-5 w-5 -translate-y-1/2 text-gray-500 dark:text-slate-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            aria-hidden
          >
            <circle cx="11" cy="11" r="6" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <input
            value={searchInput}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search by policy holder name or policy number..."
            className="h-12 w-full rounded-xl border border-gray-300 bg-white/80 dark:border-white/10 dark:bg-slate-950/40 pl-11 pr-4 text-sm font-medium text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-400 placeholder:font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40 focus-visible:border-[#14B8A6]/30 transition-colors"
          />
        </div>

        <div className="flex w-full flex-wrap items-center gap-3 md:ml-auto md:w-auto md:flex-1 md:flex-nowrap md:justify-end lg:justify-start">
          <Combobox
            items={[
              { value: "all", label: "All" },
              { value: "active", label: "Active" },
              { value: "expiring_soon", label: "Renewal Due Soon" },
              { value: "due", label: "Due Renewals" },
              { value: "expiring", label: "Expiring (0–2 Days)" },
              { value: "grace_period", label: "Grace Period" },
              { value: "lapsed", label: "Lapsed" },
            ]}
            value={activeFilter || "all"}
            onChange={(value) => onFilterChange("filter", !value || value === "all" ? null : value)}
            placeholder="Status"
            className={FILTER_CONTROL_CLASS}
            searchable={false}
          />

          <Combobox
            items={["all", "HDFC Ergo", "ICICI Lombard", "Star Health", "TATA AIG"]}
            value={carrierParam || null}
            onChange={(value) => onFilterChange("carrier", !value || value === "all" ? null : value)}
            placeholder="Policy Provider"
            className={FILTER_CONTROL_CLASS}
            searchable={false}
          />

          <Combobox
            items={["all", "Health", "Life", "Motor", "Travel"]}
            value={typeParam || null}
            onChange={(value) => onFilterChange("type", !value || value === "all" ? null : value)}
            placeholder="Policy Type"
            className={FILTER_CONTROL_CLASS}
            searchable={false}
          />

          <Combobox
            items={["all", "today", "7", "30", "past_due"]}
            value={expiryParam || null}
            onChange={(value) => onFilterChange("expiry", !value || value === "all" ? null : value)}
            placeholder="Expiry"
            className={FILTER_CONTROL_CLASS}
            searchable={false}
          />

          <Combobox
            items={[
              { value: "default", label: "Default" },
              "newest",
              "oldest",
              "expiry",
              "name",
            ]}
            value={sortParam || null}
            onChange={(value) => onFilterChange("sort", !value || value === "default" ? null : value)}
            placeholder="Sort"
            className={`${FILTER_CONTROL_CLASS} sm:w-40`}
            searchable={false}
          />
        </div>
      </div>
    </div>
  );
}

export default PolicyListToolbar;
