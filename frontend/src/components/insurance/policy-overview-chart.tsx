import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "./glass-card";

type ChartPeriod = "weekly" | "monthly" | "yearly";

type PolicyOverviewChartProps = {
  stats: {
    active: number;
    due: number;
    expiring: number;
    grace_period: number;
    lapsed: number;
    pending_followups: number;
  };
  renewalRate?: number;
};

const PERIODS: ChartPeriod[] = ["weekly", "monthly", "yearly"];

function buildSeries(stats: PolicyOverviewChartProps["stats"], period: ChartPeriod) {
  const base = [stats.active, stats.due, stats.expiring, stats.grace_period, stats.lapsed, stats.pending_followups];
  const labels =
    period === "weekly"
      ? ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
      : period === "monthly"
        ? ["W1", "W2", "W3", "W4"]
        : ["Jan", "Feb", "Mar", "Apr", "May", "Jun"];

  const max = Math.max(...base, 1);
  return labels.map((label, i) => {
    const mix = base.reduce((sum, v, j) => sum + v * ((i + j + 1) % 5), 0);
    const value = Math.max(1, Math.round((mix / (base.length * labels.length)) * 2));
    return { label, value: Math.min(value, max + 2) };
  });
}

export function PolicyOverviewChart({ stats, renewalRate }: PolicyOverviewChartProps) {
  const [period, setPeriod] = useState<ChartPeriod>("monthly");
  const series = useMemo(() => buildSeries(stats, period), [stats, period]);
  const maxVal = Math.max(...series.map((s) => s.value), 1);
  const width = 480;
  const height = 160;
  const padX = 8;
  const padY = 12;
  const step = (width - padX * 2) / (series.length - 1);

  const points = series.map((s, i) => {
    const x = padX + i * step;
    const y = height - padY - (s.value / maxVal) * (height - padY * 2);
    return `${x},${y}`;
  });

  const areaPoints = `${padX},${height - padY} ${points.join(" ")} ${padX + (series.length - 1) * step},${height - padY}`;

  return (
    <GlassCard delay={0.25} className="p-5 md:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Renewal Overview</h3>
          <p className="text-sm text-slate-400">
            Policy activity trends
            {renewalRate != null ? ` · ${renewalRate}% renewal rate` : ""}
          </p>
        </div>
        <div className="flex rounded-xl border border-white/8 bg-white/5 p-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition ${
                period === p ? "bg-[#8B5CF6]/25 text-[#C4B5FD]" : "text-slate-400 hover:text-white"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="none" aria-hidden>
          <defs>
            <linearGradient id="chartLineGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#8B5CF6" />
              <stop offset="100%" stopColor="#14B8A6" />
            </linearGradient>
            <linearGradient id="chartAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0.25, 0.5, 0.75].map((pct) => (
            <line
              key={pct}
              x1={padX}
              y1={height - padY - pct * (height - padY * 2)}
              x2={width - padX}
              y2={height - padY - pct * (height - padY * 2)}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="1"
            />
          ))}
          <motion.polygon
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            points={areaPoints}
            fill="url(#chartAreaGrad)"
          />
          <motion.polyline
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 1, ease: "easeOut" }}
            points={points.join(" ")}
            fill="none"
            stroke="url(#chartLineGrad)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ filter: "drop-shadow(0 0 8px rgba(139,92,246,0.6))" }}
          />
          {series.map((s, i) => {
            const [x, y] = points[i].split(",").map(Number);
            return <circle key={s.label} cx={x} cy={y} r="4" fill="#8B5CF6" stroke="#050816" strokeWidth="2" />;
          })}
        </svg>
        <div className="mt-2 flex justify-between px-1">
          {series.map((s) => (
            <span key={s.label} className="text-[10px] text-slate-500">
              {s.label}
            </span>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}
