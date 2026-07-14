import {
  RENEWAL_STATUS_COLORS,
  RENEWAL_STATUS_LEGEND,
  RENEWAL_STATUS_LABELS,
} from "../../lib/utils/renewal-intelligence";

export function RenewalIntelligenceLegend() {
  return (
    <div className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {RENEWAL_STATUS_LEGEND.map(({ status, description }) => (
        <div key={status} className="flex items-start gap-2.5">
          <span
            className="mt-1.5 h-2.5 w-2.5 flex-shrink-0 rounded-full"
            style={{ backgroundColor: RENEWAL_STATUS_COLORS[status] }}
          />
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-200">{RENEWAL_STATUS_LABELS[status]}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
