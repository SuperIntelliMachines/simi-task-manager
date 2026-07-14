import React from "react";
import { PropsWithChildren } from "react";

export function QuickStatCard({ title, count, eyebrow, icon, onClick }: PropsWithChildren<{ title: string; count: number; eyebrow?: string; icon?: React.ReactNode; onClick?: () => void }>) {
  const key = (title || "").toLowerCase();
  let accentHex = "#06b6d4"; // cyan default
  let accentRgba = "6,182,212";
  if (key.includes("active")) {
    accentHex = "#22c55e"; accentRgba = "34,197,94"; // green
  } else if (key.includes("due")) {
    accentHex = "#f59e0b"; accentRgba = "245,158,11"; // yellow
  } else if (key.includes("expiring")) {
    accentHex = "#fb923c"; accentRgba = "251,146,60"; // orange
  } else if (key.includes("lapsed")) {
    accentHex = "#ef4444"; accentRgba = "239,68,68"; // red
  } else if (key.includes("grace")) {
    accentHex = "#f59e0b"; accentRgba = "245,158,11"; // amber
  } else if (key.includes("follow")) {
    accentHex = "#ec4899"; accentRgba = "236,72,153"; // pink
  } else if (key.includes("total")) {
    accentHex = "#06b6d4"; accentRgba = "6,182,212"; // cyan
  }

  const glowShadow = `0 8px 24px -12px rgba(${accentRgba},0.14)`;

  return (
    <button
      onClick={onClick}
      className="relative text-left rounded-2xl bg-black/30 backdrop-blur-xl border border-white/10 p-4 hover:-translate-y-1 transition-all duration-300 cursor-pointer w-full"
      style={{ boxShadow: glowShadow }}
    >
      {/* Top accent bar (thin) */}
      <div className="absolute left-0 top-0 w-full h-0.5 rounded-t-2xl" style={{ background: `linear-gradient(90deg, ${accentHex}, ${accentHex}33)` }} />

      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-slate-300">{title}</p>

        <div>
          <div className="text-4xl font-bold text-white leading-tight">{count}</div>
        </div>
      </div>

      {/* status icon bottom-right */}
      {icon ? (
        <div className="absolute right-3 bottom-3 text-slate-300 opacity-90">{icon}</div>
      ) : null}
    </button>
  );
}

export default QuickStatCard;
