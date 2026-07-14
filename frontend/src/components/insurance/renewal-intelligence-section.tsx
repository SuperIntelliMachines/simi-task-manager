import { useMemo, useState } from "react";
import { GlassCard } from "./glass-card";
import { RenewalIntelligenceBubbleChart } from "./renewal-intelligence-bubble-chart";
import { RenewalIntelligenceDetailsTable } from "./renewal-intelligence-details-table";
import { RenewalIntelligenceLegend } from "./renewal-intelligence-legend";
import { BarChart2 } from "./icons";
import {
  filterRenewalIntelligencePoints,
  type RenewalIntelligenceChart,
} from "../../lib/utils/renewal-intelligence";

type RenewalIntelligenceSectionProps = {
  data: RenewalIntelligenceChart;
};

const selectClassName =
  "w-full rounded-xl border border-border bg-background/70 px-3 h-11 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#14B8A6]/40";

export function RenewalIntelligenceSection({ data }: RenewalIntelligenceSectionProps) {
  const [productFilter, setProductFilter] = useState("");

  const filteredPoints = useMemo(
    () => filterRenewalIntelligencePoints(data.points, productFilter),
    [data.points, productFilter]
  );

  return (
    <section className="space-y-4">
      <GlassCard delay={0.25} className="p-5 md:p-6">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#14B8A6]/15 text-[#14B8A6]">
            <BarChart2 className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Renewal Intelligence</h3>
            <p className="text-xs text-muted-foreground">Axis scales with selected policy expiry dates.</p>
          </div>
        </div>

        <RenewalIntelligenceLegend />

        <div className="my-5 max-w-md">
          <label className="block">
            <span className="mb-2 block text-sm text-muted-foreground">Product Type Filter</span>
            <select
              value={productFilter}
              onChange={(event) => setProductFilter(event.target.value)}
              className={selectClassName}
            >
              <option value="">All Product Types</option>
              {data.filters.product_types.map((productType) => (
                <option key={productType} value={productType}>
                  {productType}
                </option>
              ))}
            </select>
          </label>
        </div>

        <RenewalIntelligenceBubbleChart points={filteredPoints} />
        <RenewalIntelligenceDetailsTable points={filteredPoints} />
      </GlassCard>
    </section>
  );
}
