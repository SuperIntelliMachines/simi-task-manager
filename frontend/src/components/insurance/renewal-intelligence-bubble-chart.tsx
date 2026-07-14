import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  RENEWAL_STATUS_COLORS,
  RENEWAL_TOOLTIP_HEIGHT,
  RENEWAL_TOOLTIP_WIDTH,
  applyBubbleVisualJitter,
  buildPremiumBubbleRadii,
  buildExpiryAxisTicks,
  buildPremiumAxisTicks,
  computeRenewalTooltipPlacement,
  expiryTimeToX,
  formatExpiryLabel,
  formatPremiumInr,
  premiumToY,
  renewalStatusForPoint,
  renewalStatusLabelForPoint,
  resolveExpiryTimeScale,
  resolvePremiumScale,
  type RenewalTooltipPlacement,
  type RenewalIntelligencePoint,
} from "../../lib/utils/renewal-intelligence";

const CHART_WIDTH = 920;
const CHART_HEIGHT = 380;
const PADDING = { top: 20, right: 28, bottom: 52, left: 76 };

type RenewalIntelligenceBubbleChartProps = {
  points: RenewalIntelligencePoint[];
};

type PlottedPoint = RenewalIntelligencePoint & {
  baseX: number;
  baseY: number;
  x: number;
  y: number;
  r: number;
  clampedX: boolean;
};

function formatAxisPremium(value: number): string {
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
  if (value >= 1000) return `₹${Math.round(value / 1000)}k`;
  return `₹${Math.round(value)}`;
}

function TooltipRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 text-xs">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-200">{value}</span>
    </div>
  );
}

export function RenewalIntelligenceBubbleChart({ points }: RenewalIntelligenceBubbleChartProps) {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [tooltipPlacement, setTooltipPlacement] = useState<RenewalTooltipPlacement | null>(null);

  const layout = useMemo(() => {
    if (points.length === 0) {
      return null;
    }

    const expiryTimes = points
      .map((point) => new Date(point.expiry_date).getTime())
      .filter((value) => !Number.isNaN(value));
    const premiums = points.map((point) => point.premium);
    const timeScale = resolveExpiryTimeScale(expiryTimes);
    const premiumScale = resolvePremiumScale(premiums);
    const innerWidth = CHART_WIDTH - PADDING.left - PADDING.right;
    const innerHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;

    const bubbleRadii = buildPremiumBubbleRadii(premiums);

    const plotLeft = PADDING.left;
    const plotTop = PADDING.top;
    const plotRight = CHART_WIDTH - PADDING.right;
    const plotBottom = CHART_HEIGHT - PADDING.bottom;

    const basePlotted = points.map((point, index) => {
      const xTime = new Date(point.expiry_date).getTime();
      const baseX = Number.isNaN(xTime)
        ? plotLeft
        : expiryTimeToX(xTime, timeScale, plotLeft, innerWidth);
      const clampedX = !Number.isNaN(xTime) && xTime > timeScale.scaleMaxTime;

      return {
        point,
        baseX,
        baseY: premiumToY(point.premium, premiumScale, plotTop, innerHeight),
        r: bubbleRadii[index] ?? 7,
        clampedX,
      };
    });

    const jittered = applyBubbleVisualJitter(
      basePlotted.map(({ point, baseX, baseY, r }) => ({
        policy_id: point.policy_id,
        expiry_date: point.expiry_date,
        premium: point.premium,
        baseX,
        baseY,
        r,
      })),
      { left: plotLeft, right: plotRight, top: plotTop, bottom: plotBottom }
    );

    const plotted: PlottedPoint[] = basePlotted.map(({ point, baseX, baseY, r, clampedX }, index) => {
      const layout = jittered[index];
      return {
        ...point,
        baseX,
        baseY,
        x: layout?.x ?? baseX,
        y: layout?.y ?? baseY,
        r,
        clampedX,
      };
    });

    const xTicks = buildExpiryAxisTicks({
      minTime: timeScale.minTime,
      scaleMaxTime: timeScale.scaleMaxTime,
      paddingLeft: PADDING.left,
      innerWidth,
    });
    const yTicks = buildPremiumAxisTicks(premiumScale, 5);

    return {
      plotted,
      timeScale,
      premiumScale,
      innerWidth,
      innerHeight,
      xTicks,
      yTicks,
    };
  }, [points]);

  const hovered = layout?.plotted.find((point) => point.policy_id === hoveredId) ?? null;

  function updateTooltipPlacement(point: PlottedPoint) {
    const container = containerRef.current;
    const svg = svgRef.current;
    if (!container || !svg) return;

    const containerRect = container.getBoundingClientRect();
    const svgRect = svg.getBoundingClientRect();
    const scaleX = svgRect.width / CHART_WIDTH;
    const scaleY = svgRect.height / CHART_HEIGHT;

    setTooltipPlacement(
      computeRenewalTooltipPlacement({
        bubbleX: point.x,
        bubbleY: point.y,
        bubbleRadius: point.r,
        containerWidth: containerRect.width,
        containerHeight: Math.max(containerRect.height, svgRect.height),
        scaleX,
        scaleY,
      })
    );
  }

  function handleBubbleHover(point: PlottedPoint) {
    setHoveredId(point.policy_id);
    updateTooltipPlacement(point);
  }

  function handleBubbleLeave() {
    setHoveredId(null);
    setTooltipPlacement(null);
  }

  if (points.length === 0) {
    return (
      <div className="flex min-h-[300px] items-center justify-center rounded-xl border border-white/5 bg-slate-950/20 px-6 py-10">
        <p className="text-sm text-slate-400">No policies found for the selected filters.</p>
      </div>
    );
  }

  if (!layout) {
    return null;
  }

  const plotLeft = PADDING.left;
  const plotTop = PADDING.top;
  const plotRight = CHART_WIDTH - PADDING.right;
  const plotBottom = CHART_HEIGHT - PADDING.bottom;

  return (
    <div ref={containerRef} className="relative w-full overflow-x-auto overflow-y-visible">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        className="min-w-full"
        role="img"
        aria-label="Renewal intelligence bubble chart"
      >
        <rect
          x={plotLeft}
          y={plotTop}
          width={plotRight - plotLeft}
          height={plotBottom - plotTop}
          fill="rgba(15,23,42,0.35)"
          rx={14}
          stroke="rgba(148,163,184,0.08)"
        />

        {layout.yTicks.map((tick) => {
          const y = premiumToY(tick, layout.premiumScale, PADDING.top, layout.innerHeight);
          return (
            <g key={`y-${tick}`}>
              <line
                x1={plotLeft}
                x2={plotRight}
                y1={y}
                y2={y}
                stroke="rgba(148,163,184,0.14)"
                strokeDasharray="4 6"
              />
              <text x={plotLeft - 12} y={y + 4} textAnchor="end" className="fill-slate-500 text-[11px]">
                {formatAxisPremium(tick)}
              </text>
            </g>
          );
        })}

        {layout.xTicks.map((tick, index) => (
          <g key={`x-${tick.label}-${index}`}>
            <line
              x1={tick.x}
              x2={tick.x}
              y1={plotTop}
              y2={plotBottom}
              stroke="rgba(148,163,184,0.06)"
            />
            <text x={tick.x} y={CHART_HEIGHT - 20} textAnchor="middle" className="fill-slate-500 text-[11px]">
              {tick.label}
            </text>
          </g>
        ))}

        {layout.timeScale.hasFarFutureOutlier ? (
          <g>
            <line
              x1={plotRight}
              x2={plotRight}
              y1={plotTop}
              y2={plotBottom}
              stroke="rgba(148,163,184,0.22)"
              strokeDasharray="3 4"
            />
            <text x={plotRight - 6} y={plotTop + 12} textAnchor="end" className="fill-slate-500 text-[10px]">
              →
            </text>
          </g>
        ) : null}

        <text
          x={CHART_WIDTH / 2}
          y={CHART_HEIGHT - 4}
          textAnchor="middle"
          className="fill-slate-500 text-[11px]"
        >
          Renewal Date
        </text>
        <text
          transform={`translate(18 ${CHART_HEIGHT / 2}) rotate(-90)`}
          textAnchor="middle"
          className="fill-slate-500 text-[11px]"
        >
          Premium Amount (₹)
        </text>

        {layout.plotted.map((point) => {
          const isHovered = hoveredId === point.policy_id;
          return (
            <motion.circle
              key={point.policy_id}
              cx={point.x}
              cy={point.y}
              r={point.r}
              fill={RENEWAL_STATUS_COLORS[renewalStatusForPoint(point)]}
              fillOpacity={isHovered ? 0.95 : 0.82}
              stroke={isHovered ? "#FFFFFF" : point.clampedX ? "rgba(251,191,36,0.8)" : "rgba(255,255,255,0.28)"}
              strokeWidth={isHovered ? 1.75 : 1}
              strokeDasharray={point.clampedX ? "2 2" : undefined}
              className="cursor-pointer"
              initial={false}
              animate={{ r: isHovered ? point.r + 1 : point.r }}
              transition={{ duration: 0.16, ease: "easeOut" }}
              onMouseEnter={() => handleBubbleHover(point)}
              onMouseMove={() => handleBubbleHover(point)}
              onMouseLeave={handleBubbleLeave}
              onClick={() => navigate(`/app/insurance/policies/${point.policy_id}`)}
            />
          );
        })}
      </svg>

      <AnimatePresence mode="wait">
        {hovered && tooltipPlacement ? (
          <motion.div
            key={hovered.policy_id}
            initial={{ opacity: 0, x: tooltipPlacement.offsetX, y: tooltipPlacement.offsetY }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            exit={{ opacity: 0, x: tooltipPlacement.offsetX * 0.5, y: tooltipPlacement.offsetY * 0.5 }}
            transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
            className="pointer-events-none absolute z-20 rounded-xl border border-white/10 bg-slate-950/96 p-4 shadow-2xl backdrop-blur-md"
            style={{
              left: tooltipPlacement.x,
              top: tooltipPlacement.y,
              width: RENEWAL_TOOLTIP_WIDTH,
              minHeight: RENEWAL_TOOLTIP_HEIGHT,
            }}
          >
            <p className="truncate text-sm font-semibold uppercase tracking-wide text-white">{hovered.customer_name}</p>
            <p className="mt-0.5 truncate text-xs text-slate-500">{hovered.policy_number}</p>
            <div className="mt-3 space-y-2 border-t border-white/8 pt-3">
              <TooltipRow label="Product Type" value={hovered.product_type ?? "—"} />
              <TooltipRow label="Renewal Date" value={formatExpiryLabel(hovered.expiry_date)} />
              <TooltipRow label="Premium Amount" value={formatPremiumInr(hovered.premium)} />
              {hovered.days_overdue != null ? (
                <TooltipRow label="Days Overdue" value={String(hovered.days_overdue)} />
              ) : (
                <TooltipRow
                  label="Days Until Due"
                  value={hovered.days_until_due != null ? String(hovered.days_until_due) : "—"}
                />
              )}
              <TooltipRow label="Status" value={renewalStatusLabelForPoint(hovered)} />
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
